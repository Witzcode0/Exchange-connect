"""
API endpoints for "projects" package.
"""
import datetime
import json
import os

from werkzeug.exceptions import HTTPException, Forbidden
from flask import request, current_app, g
from flask_restful import abort
from flask_uploads import AUDIO
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import load_only
from sqlalchemy.inspection import inspect
from flasgger.utils import swag_from
from webargs.flaskparser import parser

from app import db, c_abort, projectarchivefile
from app.base.api import AuthResource
from app.base import constants as APP
from app.common.helpers import store_file
from app.auth.decorators import role_permission_required
from app.resources.roles import constants as ROLE
from app.resources.accounts.models import Account
from app.toolkit_resources.projects import constants as PROJECT
from app.toolkit_resources.projects.models import Project
from app.toolkit_resources.project_file_archive.models import (
    ProjectArchiveFile)
from app.toolkit_resources.project_status.models import ProjectStatus
from app.toolkit_resources.projects.schemas import (
    ProjectSchema, ProjectReadAdminArgsSchema, ProjectAdminAnalystPostSchema,
    ProjectAdminAnalystPutSchema)
from app.toolkit_resources.project_parameters.schemas import (
    ProjectParameterSchema)
from app.toolkit_resources.project_analysts.models import ProjectAnalyst
from app.toolkit_resources.project_designers.models import ProjectDesigner
from app.toolkit_resources.ref_project_types.models import RefProjectType
from app.toolkit_resources.projects.helpers import calculate_status
from app.resources.account_managers.models import AccountManager
from app.base.schemas import BaseCommonSchema
from queueapp.toolkits.email_tasks import (
    send_order_placed_email, send_status_change_emails,
    send_project_assigned_emails, send_analyst_requested_emails)
from app.resources.users.models import User
from app.toolkit_resources.project_history.models import ProjectHistory
from app.toolkit_resources.ref_project_sub_type.models import ProjectSubParamGroup



class ProjectAdminAnalystAPI(AuthResource):
    """
    Put, delete and get API for managing projects by admin
    """

    @role_permission_required(perms=[ROLE.EPT_NU])
    def post(self):
        """
        Create a project
        """
        project_schema = ProjectAdminAnalystPostSchema()
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
            data.admin_id = g.current_user['row_id']
            data.updated_by = data.created_by

            for d in data.project_parameters:
                d.created_by = data.created_by
                d.updated_by = data.created_by
                d.account_id = data.account_id
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
                            category=key,
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
            if data.is_draft is False:
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


    @role_permission_required(perms=[ROLE.EPT_NU])
    @swag_from('swagger_docs/project_admin_analysts_put.yml')
    def put(self, row_id):
        """
        Update a project
        """
        proj_admin_analyst_schema = ProjectAdminAnalystPutSchema()
        # first find model
        model = None
        old_is_draft = False
        old_analyst_requested = None
        try:
            model = Project.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Project id: %s does not exist' %
                                     str(row_id))
            old_is_draft = model.is_draft
            old_analyst_requested = model.analyst_requested
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
            input_data = parser.parse(
                BaseCommonSchema(), locations=('querystring',))
            prev_status_id = model.status_id
            #current_status_seq = int(json_data.get('status_id', 0))
            if 'project_parameter_delete_ids' in json_data:
                json_data['project_parameter_delete_ids'] = \
                    request.form.getlist('project_parameter_delete_ids')
            if 'analyst_ids' in json_data:
                json_data['analyst_ids'] = request.form.getlist('analyst_ids')
            if 'designer_ids' in json_data:
                json_data['designer_ids'] = request.form.getlist('designer_ids')

            # for tracking changes
            old_project = {x: getattr(model, x) for x in model.__trackcolumns__}

            # validate and deserialize input
            data, errors = proj_admin_analyst_schema.load(
                json_data, instance=model, partial=True)

            if errors:
                c_abort(422, errors=errors)
            # if (current_status_seq
            #     and (prev_status_seq != current_status_seq)
            #     and prev_status_seq != current_status_seq - 1):
            #     c_abort(422, message="Please update status with sequence"
            #                          " {} first".format(current_status_seq - 1))
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            # Project parameter creation
            if ('None' in
                    proj_admin_analyst_schema._request_project_parameters and
                    proj_admin_analyst_schema._request_project_parameters[
                    'None']):
                for row in (proj_admin_analyst_schema.
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
            for drow_id in (proj_admin_analyst_schema.
                            _cached_project_parameters):
                try:
                    pp_model = (proj_admin_analyst_schema.
                                _cached_project_parameters[drow_id])
                    # loading project_parameters_schema to update values
                    # in dictionary format after validate the key
                    projpara_json = {
                        'parent_parameter_name':
                        proj_admin_analyst_schema.
                        _request_project_parameters[drow_id]
                        ['parent_parameter_name'],
                        'parameter_name': proj_admin_analyst_schema.
                        _request_project_parameters[drow_id]['parameter_name'],
                        'parameter_value': proj_admin_analyst_schema.
                        _request_project_parameters[drow_id]['parameter_value']
                    }
                    if ('started_at' in proj_admin_analyst_schema.
                            _request_project_parameters[drow_id]):
                        projpara_json['started_at'] =\
                            (proj_admin_analyst_schema.
                                _request_project_parameters[
                                    drow_id]['started_at'])
                    if ('ended_at' in proj_admin_analyst_schema.
                            _request_project_parameters[drow_id]):
                        projpara_json['ended_at'] =\
                            (proj_admin_analyst_schema.
                                _request_project_parameters[
                                    drow_id]['ended_at'])
                    vdata, verrors = ProjectParameterSchema().load(
                        projpara_json, instance=pp_model, partial=True)
                    if verrors:
                        c_abort(422, errors=verrors)
                    # no errors, so add data to db
                    db.session.add(vdata)
                except KeyError as e:
                    continue

            db.session.add(data)
            db.session.commit()

            new_analyst_ids = []
            new_designer_ids = []
            # manage analysts
            if (proj_admin_analyst_schema._cached_analysts or
                    'analyst_ids' in json_data):
                analyst_ids = []
                for analyst in proj_admin_analyst_schema._cached_analysts:
                    if analyst not in data.analysts:
                        analyst_ids.append(analyst.row_id)
                        db.session.add(ProjectAnalyst(
                            project_id=data.row_id,
                            analyst_id=analyst.row_id,
                            created_by=g.current_user['row_id'],
                            updated_by=g.current_user['row_id']))
                        new_analyst_ids.append(analyst.row_id)
                # remove old ones
                for oldanalyst in data.project_analysts[:]:
                    if (oldanalyst.analyst not in
                            proj_admin_analyst_schema._cached_analysts):
                        if oldanalyst in data.project_analysts:
                            if oldanalyst.analyst_id:
                                db.session.delete(oldanalyst)
                                db.session.commit()
                db.session.commit()

            # manage designers
            if (proj_admin_analyst_schema._cached_designers or
                    'designer_ids' in json_data):
                for designer in proj_admin_analyst_schema._cached_designers:
                    if designer not in data.designers:
                        db.session.add(ProjectDesigner(
                            project_id=data.row_id,
                            designer_id=designer.row_id,
                            created_by=g.current_user['row_id'],
                            updated_by=g.current_user['row_id']))
                        new_designer_ids.append(designer.row_id)
                # remove old ones
                for olddesigner in data.project_designers[:]:
                    if (olddesigner.designer not in
                            proj_admin_analyst_schema._cached_designers):
                        if olddesigner in data.project_designers:
                            if olddesigner.designer_id:
                                db.session.delete(olddesigner)
                                db.session.commit()
                db.session.commit()

            file_created_by = g.current_user['row_id']
            if g.current_user['row_id'] == data.admin_id:
                file_created_by = data.created_by

            # flag to know if user is prime communicator
            prime_communicator = False
            if ((g.current_user['role']['name'] == ROLE.ERT_ANALYST
                and data.work_area in [PROJECT.DESIGN_CONTENT, PROJECT.CONTENT])
                or (g.current_user['role']['name'] == ROLE.ERT_DESIGN
                    and data.work_area == PROJECT.DESIGN)):
                prime_communicator = True
            # brand identity , logo and other file if uploaded previous will be
            # deleted
            file_category_vs_id = {}
            one_file_categories = [PROJECT.COMP_LOGO, PROJECT.BRAND_IDENTITY,
                                   PROJECT.OTHER_FILE ]
            status_to_update = []
            for key in request.files:
                if key in PROJECT.PROJECT_FILE_CATEGORY:
                    uploaded_files = request.files.getlist(key)
                    if (prime_communicator and uploaded_files
                            and key in PROJECT.CATEGORY_STATUS_CODE):
                        # project status should be changed to this
                        status_to_update.append(
                            PROJECT.CATEGORY_STATUS_CODE[key])
                    for file in uploaded_files:
                        archiv_obj = ProjectArchiveFile(
                            category=key,
                            account_id=data.account_id, project_id=data.row_id,
                            created_by=file_created_by,
                            updated_by=file_created_by)
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
                        if key in one_file_categories:
                            file_category_vs_id[key] = archiv_obj.row_id
            if file_category_vs_id:
                ProjectArchiveFile.query.filter(
                    and_(ProjectArchiveFile.category.in_(
                        file_category_vs_id.keys()),
                        ProjectArchiveFile.row_id.notin_(
                        file_category_vs_id.values()))).update({
                    'deleted': True}, synchronize_session=False)
            if not data.status_id and (data.analysts or data.designers):
                data.status_id = ProjectStatus.query.filter_by(
                code="proj_assigned").first().row_id
            if status_to_update:
                status = ProjectStatus.query.filter(
                    ProjectStatus.code.in_(status_to_update)).order_by(
                    ProjectStatus.sequence.desc()).first()
                if data.status and data.status.sequence < status.sequence:
                    data.status = status

            if prev_status_id != data.status_id:
                calculate_status(data)
                send_status_change_emails.s(True, data.row_id).delay()

            if old_is_draft and input_data.get('order'):
                data.is_draft = False
                data.order_date = datetime.datetime.utcnow()
                send_order_placed_email.s(True, data.row_id).delay()

            # send analyst requested email and notification
            if not old_analyst_requested and model.analyst_requested:
                send_analyst_requested_emails.s(True, data.row_id).delay()
            if new_designer_ids + new_analyst_ids:
                send_project_assigned_emails.s(
                    True, data.row_id, g.current_user['row_id'],
                    new_analyst_ids, new_designer_ids).delay()
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
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Updated Project id: %s' % str(row_id)}, 200

    @role_permission_required(perms=[ROLE.EPT_NU])
    @swag_from('swagger_docs/project_admin_analysts_delete.yml')
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
            model.deleted = True
            db.session.add(model)
            db.session.commit()
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204

    @role_permission_required(perms=[ROLE.EPT_NU])
    @swag_from('swagger_docs/project_admin_analysts_get.yml')
    def get(self, row_id):
        """
        Get a project by id
        """
        model = None
        try:
            # first find model
            model = Project.query.get(row_id)
            if model is None:
                c_abort(404, message='Project id: %s does not exist' %
                        str(row_id))
            # analyst and designers can only get project assigned to them
            if (g.current_user['role']['name'] in
                [ROLE.ERT_DESIGN, ROLE.ERT_ANALYST]):
                current_user = User.query.get(g.current_user['row_id'])
                if current_user not in model.analysts + model.designers:
                    abort(403)
            # project_parameters need to be display here so removing
            # from _default_exclude_fields list by making a copy
            local_exclude_list = ProjectSchema._default_exclude_fields[:]
            local_exclude_list.remove('project_parameters')
            result = ProjectSchema(exclude=local_exclude_list).dump(model)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data}, 200


class ProjectAdminAnalystListAPI(AuthResource):
    """
    Read API for project lists, i.e, more than 1 project
    """
    model_class = Project

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['account', 'creator', 'project_type',
                                    'project_analysts', 'analysts', 'admin',
                                    'designers', 'status']
        super(ProjectAdminAnalystListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        account_name = filters.get('account_name')
        project_name = filters.get('project_name')
        if account_name and project_name:
            filters.pop('account_name')
            filters.pop('project_name', None)
        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)
        # build specific extra queries filters
        if extra_query:
            pass


        query = self._build_final_query(query_filters, query_session, operator)
        query = query.join(
            Account, Project.account_id == Account.row_id)
        # manager can access assigned account project only
        if g.current_user['role']['name'] == ROLE.ERT_MNG:
            query = query.join(
                AccountManager, and_(
                    Project.account_id == AccountManager.account_id,
                    AccountManager.manager_id == g.current_user['row_id']))
        # designer can access assigned projects only
        if g.current_user['role']['name'] == ROLE.ERT_DESIGN:
            query = query.join(
                ProjectDesigner,
                ProjectDesigner.project_id == Project.row_id).filter(
                ProjectDesigner.designer_id == g.current_user['row_id'])
        # analyst can access assigned projects only
        if g.current_user['role']['name'] == ROLE.ERT_ANALYST:
            query = query.join(
                ProjectAnalyst,
                ProjectAnalyst.project_id == Project.row_id).filter(
                ProjectAnalyst.analyst_id == g.current_user['row_id'])
        if sort:
            extra_sort = True
            if 'account_name' in sort['sort_by']:
                mapper = inspect(Account)
            elif 'project_type_name' in sort['sort_by']:
                mapper = inspect(RefProjectType)
            else:
                extra_sort = False
            if extra_sort:
                sort_fxn = 'asc'
                if sort['sort'] == 'dsc':
                    sort_fxn = 'desc'
                for sby in sort['sort_by']:
                    if sby in mapper.columns:
                        order.append(getattr(mapper.columns[sby], sort_fxn)())
        query = query.join(RefProjectType)
        if account_name and project_name:
            query = query.filter(
                or_(Account.account_name.ilike('%{}%'.format(account_name)),
                    Project.project_name.ilike('%{}%'.format(project_name))))
        return query, db_projection, s_projection, order, paging

    @role_permission_required(perms=[ROLE.EPT_NU])
    @swag_from('swagger_docs/project_admin_analysts_get_list.yml')
    def get(self):
        """
        Get the list
        """
        project_read_schema = ProjectReadAdminArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            project_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Project), operator, True)
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
