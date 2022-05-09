"""
API endpoints for "projects" package.
"""

import datetime
import json
import os
import ast

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from webargs.flaskparser import parser
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from sqlalchemy.inspection import inspect
from flasgger.utils import swag_from
from sqlalchemy import and_
from flask_uploads import AUDIO

from app import db, c_abort, projectarchivefile
from app.base.api import AuthResource
from app.base import constants as APP
from app.base.schemas import BaseCommonSchema
from app.common.helpers import store_file
from app.resources.accounts import constants as ACCOUNT
from app.toolkit_resources.projects.models import Project
from app.toolkit_resources.projects.schemas import (
    ProjectSchema, ProjectReadArgsSchema, ProjectPutSchema)
from app.toolkit_resources.project_parameters.schemas import (
    ProjectParameterSchema)
from app.toolkit_resources.project_parameters.models import ProjectParameter
from app.toolkit_resources.project_file_archive.models import \
    ProjectArchiveFile
from app.toolkit_resources.ref_project_types.models import RefProjectType
from app.toolkit_resources.projects.helpers import calculate_status
from app.toolkit_resources.project_status.models import ProjectStatus
from app.toolkit_resources.projects import constants as PROJECT

from app.toolkit_resources.project_status.models import ProjectStatus
from app.toolkit_resources.projects import constants as PROJECT
from app.resources.roles import constants as ROLE
from app.toolkit_resources.project_history.models import ProjectHistory
from app.toolkit_resources.ref_project_sub_type.models import ProjectSubParamGroup

from queueapp.toolkits.email_tasks import (
    send_order_placed_email, send_project_cancelled_emails)


class ProjectAPI(AuthResource):
    """
    CRUD API for managing projects
    """

    @swag_from('swagger_docs/projects_post.yml')
    def post(self):
        """
        Create a project
        """
        project_schema = ProjectSchema()
        # get the json data from the request
        json_data = request.form
        if not json_data:
            c_abort(400)

        try:
            # get data from query string using parsing
            input_data = parser.parse(
                BaseCommonSchema(), locations=('querystring',))
            # validate and deserialize input into object
            data, errors = project_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            data.account_id = g.current_user['account_id']

            for d in data.project_parameters:
                d.created_by = g.current_user['row_id']
                d.updated_by = g.current_user['row_id']
                d.account_id = g.current_user['account_id']
            remarks = None
            if 'remarks' in json_data and json_data['remarks']:
                remarks = json_data['remarks']
            # when is_draft is false then order date update by current datetime
            if 'order' in input_data and input_data['order']:
                data.is_draft = False
                data.order_date = datetime.datetime.utcnow()
            last_status_id = ProjectStatus.query.order_by(
                ProjectStatus.sequence.desc()).first().row_id
            if data.status_id == last_status_id:
                data.completed = True
            db.session.add(data)
            db.session.commit()

            for key in request.files:
                if key in PROJECT.PROJECT_FILE_CATEGORY:
                    uploaded_files = request.files.getlist(key)
                    for file in uploaded_files:
                        archiv_obj = ProjectArchiveFile(
                            category=key, remarks=remarks,
                            account_id=data.account_id, project_id=data.row_id,
                            created_by=data.created_by,
                            updated_by=data.created_by)
                        db.session.add(archiv_obj)
                        db.session.commit()
                        sub_folder = archiv_obj.file_subfolder_name()
                        full_folder = archiv_obj.full_folder_path()
                        fpath, fname, ferrors, ftype = store_file(
                            projectarchivefile, file,
                            sub_folder=sub_folder,
                            full_folder=full_folder, detect_type=True,
                            type_only=True)
                        if ferrors:
                            db.session.delete(data)
                            db.session.commit()
                            return ferrors['message'], ferrors['code']
                        archiv_obj.filename = fname
                        archiv_obj.file_type = ftype
                        # major file type according to file extension
                        fmtype = (os.path.basename(fname)).split('.')[-1]
                        if fmtype in APP.VIDEO:
                            data.file_major_type = APP.FILETYP_VD
                        elif fmtype in AUDIO:
                            data.file_major_type = APP.FILETYP_AD
                        else:
                            data.file_major_type = APP.FILETYP_OT
                        db.session.add(archiv_obj)
                        db.session.commit()

            # project tyoe sub-child group data
            presentchild_obj = None
            if 'presentation_format' in json_data:
                temp = json.loads(json_data['presentation_format'])
                presentchild_obj = ProjectSubParamGroup(
                    project_type_id=data.project_type_id,
                    sub_parameter_id=temp['presentation_format_question_id'],
                    child_parameter_id=temp['presentation_format_answer_id'],
                    project_id=data.row_id
                )
                db.session.add(presentchild_obj)
                db.session.commit()


            esg_standard_obj = None
            if 'esg_standard' in json_data:
                temp = json.loads(json_data['esg_standard'])
                esg_standard_obj = ProjectSubParamGroup(
                    project_type_id=data.project_type_id,
                    sub_parameter_id=temp['esg_standard_question_id'],
                    child_parameter_id=temp['esg_standard_answer_id'],
                    project_id=data.row_id
                )
                db.session.add(esg_standard_obj)
                db.session.commit()

            # send order placed/project created email
            # if data.is_draft is False:
            send_order_placed_email.s(True, data.row_id).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # DETAIL:  Key (project_id, lower(parent_parameter_name::text),
                # lower(parameter_name::text))=(6, contents page,
                # list of contents) already exists.
                msg = e.orig.diag.message_detail
                column = ', '.join(
                    [s.split(':')[0].split(',')[0] for s in msg.split(
                        '(')[1:4:1]])
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (project_type_id)=(33) is not present in /
                # table "ref_project_type".
                column = e.orig.diag.message_detail.split('(')[1].split(')')[0]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Project added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @swag_from('swagger_docs/projects_put.yml')
    def put(self, row_id):
        """
        Update a project
        """
        project_put_schema = ProjectPutSchema()
        # first find model
        model = None
        try:
            model = Project.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Project id: %s does not exist' %
                                     str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            if model.cancelled:
                c_abort(422, message="Project is cancelled.")
            # old is_draft status
            old_is_draft = model.is_draft
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        # get the json data from the request
        json_data = request.form.to_dict()
        if not json_data:
            c_abort(400)

        try:
            # get data from query string using parsing
            prev_status_seq = model.status.sequence if model.status else None
            current_status_seq = int(json_data.get('status_id', 0))
            input_data = parser.parse(
                BaseCommonSchema(), locations=('querystring',))
            if 'project_parameter_delete_ids' in json_data:
                json_data['project_parameter_delete_ids'] = \
                    request.form.getlist('project_parameter_delete_ids')

            # for tracking changes
            old_project = {x: getattr(model, x) for x in model.__trackcolumns__}
            # validate and deserialize input
            data, errors = project_put_schema.load(
                json_data, instance=model, partial=True)

            if errors:
                c_abort(422, errors=errors)
            if (current_status_seq
                and (prev_status_seq != current_status_seq)
                and prev_status_seq != current_status_seq - 1):
                c_abort(422, message="Please update status with sequence"
                                     " {} first".format(current_status_seq - 1))
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            # Project parameter creation
            if ('None' in project_put_schema._request_project_parameters and
                    project_put_schema._request_project_parameters['None']):
                for row in (project_put_schema.
                        _request_project_parameters['None']):
                    row['project_id'] = row_id
                    pp_data, errors = ProjectParameterSchema().load(row)
                    if errors:
                        c_abort(422, errors=errors)
                    # no errors, so add data to db
                    pp_data.created_by = g.current_user['row_id']
                    pp_data.updated_by = pp_data.created_by
                    pp_data.account_id = model.account_id
                    db.session.add(pp_data)
            # Project parameter updation
            for drow_id in project_put_schema._cached_project_parameters:
                try:
                    pp_model = project_put_schema._cached_project_parameters[
                        drow_id]
                    # loading project_parameters_schema to update values
                    # in dictionary format after validate the key
                    projpara_json = {
                        'parent_parameter_name': project_put_schema.
                        _request_project_parameters[drow_id]
                        ['parent_parameter_name'],
                        'parameter_name': project_put_schema.
                        _request_project_parameters[drow_id]
                        ['parameter_name']}
                    if ('parameter_value' in project_put_schema.
                            _request_project_parameters[drow_id]):
                        projpara_json['parameter_value'] =\
                            (project_put_schema.
                                _request_project_parameters[
                                    drow_id]['parameter_value'])
                    vdata, verrors = ProjectParameterSchema().load(
                        projpara_json, instance=pp_model, partial=True)
                    if verrors:
                        c_abort(422, errors=verrors)
                    # no errors, so add data to db
                    db.session.add(vdata)

                except KeyError as e:
                    continue
            # delete project parameters
            if ('project_parameter_delete_ids' in json_data and
                    data.project_parameter_delete_ids):
                ProjectParameter.query.filter(and_(
                    ProjectParameter.row_id.in_(
                        data.project_parameter_delete_ids),
                    ProjectParameter.project_id == row_id)).delete(
                    synchronize_session=False)
            remarks = None
            if 'remarks' in json_data and json_data['remarks']:
                remarks = json_data['remarks']
            # adding related files
            for key in request.files:
                if key in PROJECT.PROJECT_FILE_CATEGORY:
                    uploaded_files = request.files.getlist(key)
                    for file in uploaded_files:
                        archiv_obj = ProjectArchiveFile(
                            category=key, remarks=remarks,
                            account_id=data.account_id, project_id=data.row_id,
                            created_by=data.created_by,
                            updated_by=data.created_by)
                        db.session.add(archiv_obj)
                        db.session.commit()
                        sub_folder = archiv_obj.file_subfolder_name()
                        full_folder = archiv_obj.full_folder_path()
                        fpath, fname, ferrors, ftype = store_file(
                            projectarchivefile, file,
                            sub_folder=sub_folder,
                            full_folder=full_folder, detect_type=True,
                            type_only=True)
                        if ferrors:
                            db.session.delete(archiv_obj)
                            db.session.commit()
                            return ferrors['message'], ferrors['code']
                        archiv_obj.filename = fname
                        archiv_obj.file_type = ftype
                        # major file type according to file extension
                        fmtype = (os.path.basename(fname)).split('.')[-1]
                        if fmtype in APP.VIDEO:
                            data.file_major_type = APP.FILETYP_VD
                        elif fmtype in AUDIO:
                            data.file_major_type = APP.FILETYP_AD
                        else:
                            data.file_major_type = APP.FILETYP_OT
                        db.session.add(archiv_obj)
                        db.session.commit()

            # when is_draft is false then order date update by current datetime
            if 'order' in input_data and input_data['order'] and old_is_draft:
                data.is_draft = False
                data.order_date = datetime.datetime.utcnow()
            db.session.add(data)
            db.session.commit()
            # adding project history if project changed
            project_history = {x: getattr(data, x) for x in old_project
                               if old_project[x] != getattr(data, x)}
            if project_history:
                history = ProjectHistory(
                    project_id=data.row_id,
                    created_by=g.current_user['row_id'], **project_history)
                db.session.add(history)
                db.session.commit()

            # send order placed/project created email
            if old_is_draft is True and data.is_draft is False:
                send_order_placed_email.s(True, data.row_id).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # DETAIL:  Key (project_id, lower(parent_parameter_name::text),
                # lower(parameter_name::text))=(6, contents page,
                # list of contents) already exists.
                msg = e.orig.diag.message_detail
                column = ', '.join(
                    [s.split(':')[0].split(',')[0] for s in msg.split(
                        '(')[1:4:1]])
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            elif APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (project_type_id)=(33) is not present in /
                # table "ref_project_type".
                column = e.orig.diag.message_detail.split('(')[1].split(')')[0]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Updated Project id: %s' % str(row_id)}, 200

    @swag_from('swagger_docs/projects_delete.yml')
    def delete(self, row_id):
        """
        Delete a project
        """
        model = None
        try:
            # first find model
            model = Project.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Project id: %s does not exist' %
                        str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            # deleting archive files related to particular project
            ProjectArchiveFile.query.filter(
                ProjectArchiveFile.project_id == row_id).delete(
                synchronize_session=False)
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

    @swag_from('swagger_docs/projects_get.yml')
    def get(self, row_id):
        """
        Get a project by id
        """

        model = None
        try:
            # first find model
            model = Project.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Project id: %s does not exist' %
                        str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            # project_parameters need to be display here so removing
            # from _default_exclude_fields list by making a copy
            local_exclude_list = ProjectSchema._default_exclude_fields[:]
            local_exclude_list.remove('project_parameters')
            result = ProjectSchema(exclude=local_exclude_list).dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data}, 200


class ProjectListAPI(AuthResource):
    """
    Read API for project lists, i.e, more than 1 project
    """
    model_class = Project

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['account', 'creator', 'project_type',
                                    'project_analysts', 'analysts', 'admin',
                                    'designers', 'status']
        super(ProjectListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)
        mapper = inspect(RefProjectType)
        # build specific extra queries filters
        if extra_query:
            pass

        query_filters['base'].append(
            Project.created_by == g.current_user['row_id'])

        if sort:
            sort_fxn = 'asc'
            if sort['sort'] == 'dsc':
                sort_fxn = 'desc'
            for sby in sort['sort_by']:
                if sby in mapper.columns:
                    order.append(getattr(mapper.columns[sby], sort_fxn)())

        query = self._build_final_query(query_filters, query_session, operator)
        query = query.join(RefProjectType)

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/projects_get_list.yml')
    def get(self):
        """
        Get the list
        """
        project_read_schema = ProjectReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            project_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Project), operator)
            # making a copy of the main output schema
            project_schema = ProjectSchema(
                exclude=ProjectSchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                project_schema = ProjectSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching projects found')
            result = project_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class ProjectCancelledAPI(AuthResource):
    """
    API for project cancelled feature
    """

    def put(self, row_id):
        """
        Update a project cancelled value
        """
        try:
            model = Project.query.get(row_id)
            if model is None:
                c_abort(404, message='Project id: %s'
                        'does not exist' % str(row_id))

            # check ownership
            if (model.created_by != g.current_user['row_id']
                and g.current_user['role']['name'] != ROLE.ERT_SU
                and (not model.account.account_manager
                     or model.account.account_manager.manager_id !=
                     g.current_user['row_id'])):
                abort(403)
            if model.status and model.status.code == PROJECT.COMPLETED:
                c_abort(422, message='Completed project can not be cancelled.')
            if not model.cancelled:
                model.cancelled = True
                db.session.add(model)
                db.session.commit()
                # send cancel notification emails.
                send_project_cancelled_emails.s(True, model.row_id).delay()
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Cancelled Project id: %s' %
                str(row_id)}, 200