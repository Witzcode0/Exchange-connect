"""
API endpoints for "file archives" package.
"""
import os

from werkzeug.exceptions import Forbidden, HTTPException
from sqlalchemy.exc import IntegrityError
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy import func, and_
from sqlalchemy.orm import load_only, joinedload
from sqlalchemy.inspection import inspect
from flask_uploads import AUDIO
from flasgger.utils import swag_from

from app import db, c_abort, projectarchivefile
from app.base.api import AuthResource
from app.base import constants as APP
from app.resources.accounts import constants as ACCOUNT
from app.common.helpers import store_file, delete_files
from app.toolkit_resources.project_file_archive.models import (
    ProjectArchiveFile)
from app.toolkit_resources.project_file_archive.schemas import (
    ProjectArchiveFileSchema, ProjectArchiveFileReadArgsSchema)
from app.toolkit_resources.projects.models import Project
from app.toolkit_resources.project_parameters.models import ProjectParameter
from app.toolkit_resources.ref_project_types.models import RefProjectType
from app.toolkit_resources.project_file_archive import constants as FILEARCHIVE
from app.toolkit_resources.projects import constants as PROJECT
from app.toolkit_resources.project_status.models import ProjectStatus
from app.resources.roles import constants as ROLE
from app.toolkit_resources.projects.helpers import calculate_status
from app.toolkit_resources.project_analysts.models import ProjectAnalyst
from app.toolkit_resources.project_designers.models import ProjectDesigner

from queueapp.toolkits.email_tasks import send_status_change_emails


class ProjectArchiveFileAPI(AuthResource):
    """
    Create, update, delete API for archive files
    """
    @swag_from('swagger_docs/project_file_archive_post.yml')
    def post(self):
        """
        Create a file
        """
        project_archive_file_schema = ProjectArchiveFileSchema()
        # get the json data from the request
        json_data = request.form
        project = None
        try:
            # validate and deserialize input into object
            data, errors = project_archive_file_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            # for account_id of project
            project = Project.query.get(data.project_id)
            data.account_id = project.account_id
            db.session.add(data)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (project_id)=(425) is not present in table "project".
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        file_data = {'files': {}, 'types': {}}
        sub_folder = data.file_subfolder_name()
        full_folder = data.full_folder_path()
        if 'filename' in request.files:
            # new file being added
            # add new file
            fpath, fname, ferrors, ftype = store_file(
                projectarchivefile, request.files['filename'],
                sub_folder=sub_folder,
                full_folder=full_folder, detect_type=True, type_only=True)
            if ferrors:
                db.session.delete(data)
                db.session.commit()
                return ferrors['message'], ferrors['code']
            file_data['files'][fname] = fpath
            file_data['types'][fname] = ftype
        else:
            db.session.delete(data)
            db.session.commit()
            c_abort(400, message='No file provided')

        try:
            if file_data and (file_data['files'] or 'delete' in file_data):
                # populate db data from file_data
                # parse new files
                if file_data['files']:
                    data.filename = [f for f in file_data['files']][0]
                    data.file_type = file_data['types'][data.filename]
                    # major file type according to file extension
                    fmtype = (os.path.basename(fname)).split('.')[-1]
                    if fmtype in APP.VIDEO:
                        data.file_major_type = APP.FILETYP_VD
                    elif fmtype in AUDIO:
                        data.file_major_type = APP.FILETYP_AD
                    else:
                        data.file_major_type = APP.FILETYP_OT
            if ((g.current_user['role']['name'] == ROLE.ERT_ANALYST
                 and project.work_area in
                    [PROJECT.DESIGN_CONTENT, PROJECT.CONTENT])
                    or (g.current_user['role']['name'] == ROLE.ERT_DESIGN
                        and project.work_area == PROJECT.DESIGN)):

                if (data.category in PROJECT.CATEGORY_STATUS_CODE
                    and data.visible_to_client):
                    # the file uploaded might change the status of project
                    status = ProjectStatus.query.filter_by(
                    code=PROJECT.CATEGORY_STATUS_CODE[data.category]).first()
                    if (project.status
                        and project.status.sequence < status.sequence):
                        # by adding file, status can change to only +ve direction
                        project.status = status
                        calculate_status(project)
                        send_status_change_emails.s(True, project.row_id).delay()

            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()

        except HTTPException as e:
            db.session.rollback()
            db.session.delete(data)
            db.session.commit()
            raise e
        except Exception as e:
            db.session.rollback()
            db.session.delete(data)
            db.session.commit()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'File Added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @swag_from('swagger_docs/project_file_archive_put.yml')
    def put(self, row_id):
        """
        Update a archive file, pass file data as multipart-form
        """
        project_archive_file_schema = ProjectArchiveFileSchema()
        # first find model
        model = None
        prev_approved = None
        try:
            model = ProjectArchiveFile.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='File id: %s does not exist' %
                                     str(row_id))
            prev_approved = model.is_approved

            # check ownership
            if g.current_user['row_id'] not in [
                model.project.created_by, model.created_by,
                model.project.admin_id]:
                abort(403)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        json_data = request.form
        file_data = {'files': {}, 'types': {}}
        sub_folder = model.file_subfolder_name()
        full_folder = model.full_folder_path()
        if not json_data and 'filename' not in request.files:
            c_abort(400)

        if 'filename' in request.files:
            # new file being added
            # check if there is already a file, then delete it, then add new
            if model.filename:
                ferrors = delete_files(
                    [model.filename], sub_folder=sub_folder,
                    full_folder=full_folder)
                if ferrors:
                    return ferrors['message'], ferrors['code']
            # add new file
            fpath, fname, ferrors, ftype = store_file(
                projectarchivefile, request.files['filename'],
                sub_folder=sub_folder,
                full_folder=full_folder, detect_type=True, type_only=True)
            if ferrors:
                return ferrors['message'], ferrors['code']
            file_data['files'][fname] = fpath
            file_data['types'][fname] = ftype

        try:
            if file_data and (file_data['files'] or 'delete' in file_data):
                # populate db data from file_data
                data = model
                # parse new files
                if file_data['files']:
                    data.filename = [f for f in file_data['files']][0]
                    data.file_type = file_data['types'][data.filename]
            if json_data:
                # validate and deserialize input
                data, errors = project_archive_file_schema.load(
                    json_data, instance=model, partial=True)
                if errors:
                    c_abort(422, errors=errors)

            status_codes = {
                PROJECT.TEMPLATE: "template_approved"}

            if (not prev_approved and data.is_approved
                    and data.category in status_codes):
                approved_status = ProjectStatus.query.filter_by(
                    code=status_codes[data.category]).first()
                if (data.project.status and
                        data.project.status.sequence < approved_status.sequence):
                    data.project.status_id = approved_status.row_id

                calculate_status(data.project)
                send_status_change_emails.s(True, data.project.row_id).delay()

            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (project_id)=(425) is not present in table "project".
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Updated File id: %s' % str(row_id)}, 200

    @swag_from('swagger_docs/project_file_archive_delete.yml')
    def delete(self, row_id):
        """
        Delete a file
        """
        model = None
        try:
            # first find model
            model = ProjectArchiveFile.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='File id: %s does not exist' %
                                     str(row_id))
            # check ownership
            if (model.created_by != g.current_user['row_id']
                and model.project.admin_id != g.current_user['row_id']):
                abort(403)

            # if model is found, and not yet deleted, delete it
            model.deleted = True
            db.session.add(model)
            db.session.commit()

        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204

    @swag_from('swagger_docs/project_file_archive_get.yml')
    def get(self, row_id):
        """
        Get a project file by id
        """
        project_archive_file_schema = ProjectArchiveFileSchema(
            exclude=ProjectArchiveFileSchema._default_exclude_fields)
        model = None
        try:
            # first find model
            model = ProjectArchiveFile.query.options(joinedload(
                ProjectArchiveFile.account)).get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='File id: %s does not exist' %
                                     str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            result = project_archive_file_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result}, 200


class ProjectArchiveFileListAPI(AuthResource):
    """
    Read API for library file lists, i.e, more than 1 library file
    """
    model_class = ProjectArchiveFile

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['file_url', 'creator', 'project',
                                    'project_parameter']
        super(ProjectArchiveFileListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        project_id = filters['project_id']
        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)
        mapper = inspect(ProjectArchiveFile)
        main_filter = None
        # build specific extra queries filters
        if extra_query:
            if 'is_draft' in extra_query:
                query_filters['filters'].append(
                    Project.is_draft.is_(extra_query['is_draft']))
            if 'project_type_id' in extra_query and extra_query[
                    'project_type_id']:
                query_filters['filters'].append(
                    Project.project_type_id == filters['project_type_id'])
            if 'project_name' in extra_query and extra_query['project_name']:
                query_filters['filters'].append(func.lower(
                    Project.project_name).like(
                        '%' + filters['project_name'].lower() + '%'))
            if 'main_filter' in extra_query and extra_query['main_filter']:
                main_filter = extra_query['main_filter']

        if g.current_user['account_type'] != ACCOUNT.ACCT_ADMIN:
            query_filters['base'].append(
                ProjectArchiveFile.account_id == g.current_user['account_id'])

        if not main_filter or main_filter == FILEARCHIVE.MNFT_ALL:
            pass
        elif main_filter == FILEARCHIVE.MNFT_MINE:
            query_filters['base'].append(
                ProjectArchiveFile.created_by == g.current_user['row_id'])
        elif main_filter == FILEARCHIVE.MNFT_RECEIVED:
            query_filters['base'].append(
                ProjectArchiveFile.created_by != g.current_user['row_id'])
        # only visible to client files
        query_filters['base'].append(
            ProjectArchiveFile.visible_to_client == True)

        if 'project_name' in sort['sort_by']:
            mapper = inspect(Project)
        elif 'project_type_name' in sort['sort_by']:
            mapper = inspect(RefProjectType)
        elif 'parent_parameter_name' in sort['sort_by']:
            mapper = inspect(ProjectParameter)
        if sort:
            sort_fxn = 'asc'
            if sort['sort'] == 'dsc':
                sort_fxn = 'desc'
            for sby in sort['sort_by']:
                if sby in mapper.columns:
                    order.append(getattr(mapper.columns[sby], sort_fxn)())

        query = self._build_final_query(query_filters, query_session, operator)
        query = query.join(
            Project, Project.row_id==ProjectArchiveFile.project_id).join(
            ProjectParameter,
            ProjectArchiveFile.project_parameter_id ==
            ProjectParameter.row_id, isouter=True).join(RefProjectType)
        project = Project.query.get(project_id)

        # only helper analysts file and designer files in case
        # of design + content not visible
        query = query.join(
            ProjectAnalyst, and_(
                ProjectAnalyst.project_id == Project.row_id,
                ProjectAnalyst.analyst_id == ProjectArchiveFile.created_by),
            isouter=True).join(
            ProjectDesigner, and_(
                ProjectDesigner.project_id == Project.row_id,
                ProjectDesigner.designer_id == ProjectArchiveFile.created_by),
            isouter=True)
        # this api is intended to be used by only client, so
        # excluding files of non prime communicators
        if project.work_area in [PROJECT.DESIGN_CONTENT, PROJECT.CONTENT]:
            query = query.filter(ProjectDesigner.row_id.is_(None))
        else:
            query = query.filter(ProjectAnalyst.row_id.is_(None))

        query = query.options(joinedload(ProjectArchiveFile.account))

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/project_file_archive_get_list.yml')
    def get(self):
        """
        Get the list
        """
        project_archive_file_read_schema = ProjectArchiveFileReadArgsSchema(
            strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            project_archive_file_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(ProjectArchiveFile),
                                 operator)
            # making a copy of the main output schema
            project_archive_file_schema = ProjectArchiveFileSchema(
                exclude=ProjectArchiveFileSchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                project_archive_file_schema = ProjectArchiveFileSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching files found')
            result = project_archive_file_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
