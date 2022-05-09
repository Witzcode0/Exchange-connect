"""
Api for events calendar
"""

from werkzeug.exceptions import HTTPException
from flask import current_app
from flask_restful import abort
from sqlalchemy.orm import load_only
from sqlalchemy import and_
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.resources.event_calendars.schemas import \
    EventCalendarSchema, EventCalenderReadArgsSchema
from app.corporate_access_resources.corporate_access_events.models import \
    CorporateAccessEvent
from app.webinar_resources.webinars.models import Webinar
from app.webcast_resources.webcasts.models import Webcast
from app.resources.event_calendars.helpers import (
    add_logo_url, corporate_query, webinar_query, webcast_query)


class EventCalendarListAPI(AuthResource):
    """
    Api for event calendar
    """

    def __init__(self, *args, **kwargs):
        super(EventCalendarListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        query_filters, extra_query, db_projection, s_projection, order, \
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)

        query_filters['base'] = [and_(
            CorporateAccessEvent.cancelled.is_(False),
            CorporateAccessEvent.is_draft.is_(False))]
        corporate_final_query = corporate_query(
            filters, query_filters, operator)

        query_filters['base'] = [and_(
            Webinar.cancelled.is_(False),
            Webinar.is_draft.is_(False))]
        webinar_final_query = webinar_query(filters, query_filters, operator)

        query_filters['base'] = [and_(
            Webcast.cancelled.is_(False),
            Webcast.is_draft.is_(False))]
        webcast_final_query = webcast_query(filters, query_filters, operator)

        final_query = corporate_final_query.union(webinar_final_query).union(
            webcast_final_query)
        order = []
        return final_query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/event_calendars_get_list.yml')
    def get(self):
        """
        Get the list
        """
        global_activity_read_schema = EventCalenderReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            global_activity_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(CorporateAccessEvent),
                                 operator)
            # making a copy of the main output schema
            event_calendar_schema = EventCalendarSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                event_calendar_schema = EventCalendarSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching events found')
            result = event_calendar_schema.dump(models, many=True)
            result_url = add_logo_url(result.data)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data, 'total': total}, 200
