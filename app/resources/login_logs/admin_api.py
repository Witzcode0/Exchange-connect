from sqlalchemy.orm import load_only
from flasgger import swag_from
from werkzeug.exceptions import HTTPException
from flask_restful import abort
from flask import current_app

from app.base.api import AuthResource
from app.auth.decorators import role_permission_required
from app import c_abort, db
from app.resources.login_logs.models import LoginLog
from app.resources.login_logs.schemas import (
    LoginLogSchema, LoginLogReadArgsSchema)
from app.resources.roles import constants as ROLE


class LoginLogListAPI(AuthResource):
    """
    Read API for login log lists, i.e, more than 1
    """
    model_class = LoginLog

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['user']
        super(LoginLogListAPI, self).__init__(*args, **kwargs)

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

        query = self._build_final_query(
            query_filters, query_session, operator)
        return query, db_projection, s_projection, order, paging

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA])
    @swag_from('swagger_docs/login_logs_getlist.yml')
    def get(self):
        """
        Get the list
        """
        total = 0
        # print(ass)
        login_log_read_schema = LoginLogReadArgsSchema(
            strict=True)
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            login_log_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(LoginLog),
                                 operator)
            # making a copy of the main output schema
            login_log_schema = LoginLogSchema()

            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                login_log_schema = LoginLogSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching login logs found')

            result = login_log_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
