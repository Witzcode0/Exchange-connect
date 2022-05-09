"""
API endpoints for "project_history" package.
"""
import datetime
import os

from werkzeug.exceptions import HTTPException, Forbidden
from flask import request, current_app, g
from flask_restful import abort
from flask_uploads import AUDIO
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, func
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
from app.toolkit_resources.project_history.models import ProjectHistory
from app.toolkit_resources.project_designers.models import ProjectDesigner
from app.toolkit_resources.project_analysts.models import ProjectAnalyst
from app.toolkit_resources.ref_project_types.models import RefProjectType
from app.toolkit_resources.project_status.models import ProjectStatus
from app.toolkit_resources.project_history.schemas import (
    ProjectHistorySchema, ProjectHistoryReadArgsSchema)
from app.resources.account_managers.models import AccountManager
from app.base.schemas import BaseCommonSchema
from queueapp.toolkits.email_tasks import (
    send_order_placed_email, send_status_change_emails,
    send_project_assigned_emails, send_analyst_requested_emails)
from app.resources.users.models import User


class ProjectHistoryAdminAnalystAPI(AuthResource):
    """
    Put, delete and get API for managing project_history by admin
    """


    @role_permission_required(perms=[ROLE.EPT_NU])
    # @swag_from('swagger_docs/project_admin_analysts_get.yml')
    def get(self, row_id):
        """
        Get a project_history by id
        """
        model = None
        try:
            # first find model
            model = ProjectHistory.query.get(row_id)
            if model is None:
                c_abort(404, message='ProjectHistory id: %s does not exist' %
                        str(row_id))
            # analyst and designers can only get project assigned to them
            if (g.current_user['role']['name'] in
                [ROLE.ERT_DESIGN, ROLE.ERT_ANALYST]):
                current_user = User.query.get(g.current_user['row_id'])
                if current_user not in model.analysts + model.designers:
                    abort(403)
            # project_parameters need to be display here so removing
            # from _default_exclude_fields list by making a copy
            result = ProjectHistorySchema().dump(model)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data}, 200


class ProjectHistoryAdminAnalystListAPI(AuthResource):
    """
    Read API for project lists, i.e, more than 1 project
    """
    model_class = ProjectHistory

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['creator', 'project_type', 'status']
        super(ProjectHistoryAdminAnalystListAPI, self).__init__(*args, **kwargs)

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
        # build specific extra queries filters
        if extra_query:
            pass


        query = self._build_final_query(query_filters, query_session, operator)
        query = query.join(
            Project, Project.row_id == ProjectHistory.project_id)
        # manager can access assigned account project history only
        if g.current_user['role']['name'] == ROLE.ERT_MNG:
            query = query.join(
                AccountManager, and_(
                    Project.account_id == AccountManager.account_id,
                    AccountManager.manager_id == g.current_user['row_id']))
        # designer can access history of assigned project only
        if g.current_user['role']['name'] == ROLE.ERT_DESIGN:
            query = query.join(
                ProjectDesigner,
                ProjectDesigner.project_id == ProjectHistory.row_id).filter(
                ProjectDesigner.designer_id == g.current_user['row_id'])
        # analyst can access assigned project_history only
        if g.current_user['role']['name'] == ROLE.ERT_ANALYST:
            query = query.join(
                ProjectAnalyst,
                ProjectAnalyst.project_id == ProjectHistory.row_id).filter(
                ProjectAnalyst.analyst_id == g.current_user['row_id'])
        if sort:
            extra_sort = True
            if 'account_name' in sort['sort_by']:
                query = query.join(
                    Account, ProjectHistory.account_id==Account.row_id)
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

        return query, db_projection, s_projection, order, paging

    @role_permission_required(perms=[ROLE.EPT_NU])
    # @swag_from('swagger_docs/project_admin_analysts_get_list.yml')
    def get(self):
        """
        Get the list
        """
        project_read_schema = ProjectHistoryReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            project_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(ProjectHistory), operator, True)
            # making a copy of the main output schema
            project_schema = ProjectHistorySchema(
                exclude=ProjectHistorySchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                project_schema = ProjectHistorySchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching project_history found')
            result = project_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
