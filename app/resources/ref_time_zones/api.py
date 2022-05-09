"""
API endpoints for "time zone" package.
"""

from werkzeug.exceptions import HTTPException
from flask import current_app
from flask_restful import abort
from sqlalchemy.orm import load_only
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.resources.ref_time_zones.models import RefTimeZone
from app.resources.ref_time_zones.schemas import (
    RefTimeZoneSchema, RefTimeZoneReadArgsSchema)


class RefTimeZoneListApi(AuthResource):
    """
    Read API for time zone lists, i.e, more than 1 time zone
    """
    model_class = RefTimeZone

    def __init__(self, *args, **kwargs):
        super(RefTimeZoneListApi, self).__init__(*args, **kwargs)

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

    @swag_from('swagger_docs/ref_time_zone_get_list.yml')
    def get(self):
        """
        Get the list
        """
        ref_time_zone_read_schema = RefTimeZoneReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            ref_time_zone_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(RefTimeZone), operator)
            # making a copy of the main output schema
            ref_time_zone_schema = RefTimeZoneSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                ref_time_zone_schema = RefTimeZoneSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching time zones found')
            result = ref_time_zone_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
