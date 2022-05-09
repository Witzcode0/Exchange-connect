"""
API endpoints for "Ir Module admin API" package.
"""
from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.orm import load_only, joinedload
from sqlalchemy.exc import IntegrityError
from marshmallow.exceptions import ValidationError
from sqlalchemy import and_, any_, func, literal

from app.base import constants as APP
from app import db, c_abort
from app.base.api import AuthResource
from app.auth.decorators import role_permission_required
from app.resources.roles import constants as ROLE
from app.resources.ir_module.models import (
    IrModule,
    IrModuleHeading,
    favirmodule)
from app.resources.ir_module.schemas import (
    IrModuleSchema,
    IrModuleHeadingSchema,
    IrModuleReadArgsSchema)

class IrModuleAdminListAPI(AuthResource):
    """
    Read API for ir module, i.e, more than 1
    """
    model_class = IrModule

    def __init__(self, *args, **kwargs):
        super(IrModuleAdminListAPI, self).__init__(*args, **kwargs)

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

        module_name = None

        if extra_query:
            if "module_name" in extra_query and extra_query['module_name']:
                module_name = extra_query.pop('module_name')
                query_filters['filters'].append(IrModule.module_name == module_name)

        query = self._build_final_query(
            query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
            ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    def get(self):
        """
        Get the list
        """
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            IrModuleReadArgsSchema(strict=True))

        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(IrModule),
                                 operator)

            # making a copy of the main output schema
            ir_module_schema = IrModuleSchema(exclude=['headings'])
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                ir_module_schema = IrModuleSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching ir modules found')
            result = ir_module_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
