"""
API endpoints for "webinar stats" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import current_app, g
from flask_restful import abort
from sqlalchemy.orm import load_only
from sqlalchemy.sql import func
from flasgger.utils import swag_from
from sqlalchemy import or_, and_, inspect, any_

from app import db, c_abort
from app.base.api import AuthResource
from app.webinar_resources.webinar_stats.models import WebinarStats
from app.webinar_resources.webinars.models import Webinar
from app.webinar_resources.webinar_attendees.models import WebinarAttendee
from app.webinar_resources.webinar_hosts.models import WebinarHost
from app.webinar_resources.webinar_invitees.models import WebinarInvitee
from app.webinar_resources.webinar_participants.models import (
    WebinarParticipant)

from app.webinar_resources.webinar_stats.schemas import (
    WebinarStatsSchema, WebinarStatsReadArgsSchema, WebinarStatsOverallSchema,
    WebinarStatsOverallReadArgsSchema)
from app.resources.event_calendars.helpers import webinar_query


class WebinarStatsAPI(AuthResource):
    """
    Get API for managing webinar stats
    """

    @swag_from('swagger_docs/webinar_stats_get.yml')
    def get(self, row_id):
        """
        Get a webinar stats by id
        """
        webinar_stats_schema = WebinarStatsSchema()
        model = None
        try:
            # first find model
            model = WebinarStats.query.get(row_id)
            if model is None:
                c_abort(404, message='Webinar Stats id: %s does not exist' %
                        str(row_id))
            result = webinar_stats_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class WebinarStatsListAPI(AuthResource):
    """
    Read API for webinar stats lists, i.e, more than 1 stat
    """
    model_class = WebinarStats

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['webinar']
        super(WebinarStatsListAPI, self).__init__(*args, **kwargs)

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

    @swag_from('swagger_docs/webinar_stats_get_list.yml')
    def get(self):
        """
        Get the list
        """
        webinar_stats_read_schema = WebinarStatsReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            webinar_stats_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(WebinarStats), operator)
            # making a copy of the main output schema
            webinar_stats_schema = WebinarStatsSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                webinar_stats_schema = WebinarStatsSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(
                    404, message='No matching webinar stats found')
            result = webinar_stats_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class WebinarStatsOverallAPI(AuthResource):
    """
    Get API for managing webinar stats overall
    """

    model_class = Webinar

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

        # excluding draft and cancelled webinars
        query_filters['base'].extend([
            Webinar.is_draft == False, Webinar.cancelled == False])
        final_query = webinar_query(filters, query_filters, operator)
        subquery = final_query.subquery()
        webinar_stats_query = db.session.query(
            func.distinct(func.count(subquery.c.row_id)).label('total_webinars'),
            func.count(subquery.c.invited).label('webinars_invited'),
            func.count(subquery.c.attended).label('webinars_attended'),
            func.count(subquery.c.hosted).label('webinars_hosted'),
            func.count(subquery.c.participated).label(
                'webinars_participated'))

        return webinar_stats_query

    @swag_from('swagger_docs/webinar_stats_overall_get.yml')
    def get(self):
        """
        Get webinar stats overall
        """
        webinar_overall_stats_args_schema = \
            WebinarStatsOverallReadArgsSchema(strict=True)
        webinar_overall_stats_schema = WebinarStatsOverallSchema()
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            webinar_overall_stats_args_schema)
        try:
            # build the sql query
            count_query = self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Webinar),
                                 operator)

            count_model = count_query.first()
            if not count_model:
                c_abort(404, message='No matching webinar stats found')
            result = webinar_overall_stats_schema.dump(count_model)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data}, 200
