"""
API endpoints for "account stats" package.
"""

from werkzeug.exceptions import HTTPException
from flask import current_app
from flask_restful import abort
from sqlalchemy.orm import load_only
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.auth.decorators import role_permission_required
from app.resources.account_stats.models import AccountStats
from app.resources.account_stats.schemas import (
    AccountStatsSchema, AccountStatsReadArgsSchema)
from app.resources.roles import constants as ROLE


class AccountStatsList(AuthResource):
    """
    Read API for account stats lists, i.e, more than 1 account stats
    """
    model_class = AccountStats

    def __init__(self, *args, **kwargs):
        super(AccountStatsList, self).__init__(*args, **kwargs)

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

        return query, db_projection, s_projection, order, paging

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[ROLE.ERT_SU])
    def get(self):
        """
        Get the list
        """
        account_stats_read_schema = AccountStatsReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            account_stats_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(AccountStats), operator)
            # making a copy of the main output schema
            account_stats_schema = AccountStatsSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                account_stats_schema = AccountStatsSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching account stats found')
            result = account_stats_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data, 'total': total}, 200