"""
API endpoints for "webcast stats" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import current_app, g
from flask_restful import abort
from sqlalchemy.sql import func
from sqlalchemy.orm import load_only
from flasgger.utils import swag_from
from sqlalchemy import inspect, and_, or_

from app import db, c_abort
from app.base.api import AuthResource
from app.webcast_resources.webcast_stats.models import WebcastStats
from app.webcast_resources.webcasts.models import Webcast
from app.webcast_resources.webcast_invitees.models import WebcastInvitee
from app.webcast_resources.webcast_hosts.models import WebcastHost
from app.webcast_resources.webcast_participants.models import WebcastParticipant
from app.webcast_resources.webcast_attendees.models import WebcastAttendee
from app.webcast_resources.webcast_stats.schemas import (
    WebcastStatsSchema, WebcastStatsReadArgsSchema,
    WebcastStatsOverallSchema, WebinarStatsOverallReadArgsSchema)
from app.resources.event_calendars.helpers import webcast_query


class WebcastStatsAPI(AuthResource):
    """
    Get API for managing webcast stats
    """

    @swag_from('swagger_docs/webcast_stats_get.yml')
    def get(self, row_id):
        """
        Get a webcast stats by id
        """
        webcast_stats_schema = WebcastStatsSchema()
        model = None
        try:
            # first find model
            model = WebcastStats.query.get(row_id)
            if model is None:
                c_abort(404, message='Webcast Stats id: %s does not exist' %
                        str(row_id))
            result = webcast_stats_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class WebcastStatsListAPI(AuthResource):
    """
    Read API for webcast stats lists, i.e, more than 1 stat
    """
    model_class = WebcastStats

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['webcast']
        super(WebcastStatsListAPI, self).__init__(*args, **kwargs)

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

    @swag_from('swagger_docs/webcast_stats_get_list.yml')
    def get(self):
        """
        Get the list
        """
        webcast_stats_read_schema = WebcastStatsReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            webcast_stats_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(WebcastStats), operator)
            # making a copy of the main output schema
            webcast_stats_schema = WebcastStatsSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                webcast_stats_schema = WebcastStatsSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(
                    404, message='No matching webcast stats found')
            result = webcast_stats_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class WebcastStatsOverallAPI(AuthResource):
    """
    Get API for managing webcast stats overall
    """

    model_class = Webcast

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
        # build specific extra queries filters
        if extra_query:
            mapper = inspect(self.model_class)
            for f in extra_query:
                # dates
                if f in ['started_at_from', 'started_at_to',
                         'ended_at_from', 'ended_at_to'] and extra_query[f]:
                    # get actual field name
                    fld = f.replace('_from', '').replace('_to', '')
                    # build date query
                    if '_from' in f:
                        query_filters['filters'].append(
                            mapper.columns[fld] >= filters[f])
                        continue
                    if '_to' in f:
                        query_filters['filters'].append(
                            mapper.columns[fld] <= filters[f])
                        continue

        # excluding draft and cancelled webcasts
        query_filters['base'].extend([
            Webcast.is_draft==False, Webcast.cancelled==False])
        webcast_final_query = webcast_query(filters, query_filters, operator)
        webcast_subquery = webcast_final_query.subquery()
        webcast_stats_query = db.session.query(
            func.count(webcast_subquery.c.row_id).label('total_webcasts'),
            func.count(webcast_subquery.c.invited).label('webcasts_invited'),
            func.count(webcast_subquery.c.hosted).label('webcasts_hosted'),
            func.count(webcast_subquery.c.participated).label(
                'webcasts_participated'))

        return webcast_stats_query

    @swag_from('swagger_docs/webcast_stats_overall_get.yml')
    def get(self):
        """
        Get webcast stats overall
        """
        webcast_overall_stats_args_schema = WebinarStatsOverallReadArgsSchema(
            strict=True)
        webcast_overall_stats_schema = WebcastStatsOverallSchema()
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            webcast_overall_stats_args_schema)
        try:
            # build the sql query
            count_query = self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Webcast),
                                 operator)

            count_model = count_query.first()
            if not count_model:
                c_abort(404, message='No matching webcast stats found')
            result = webcast_overall_stats_schema.dump(count_model)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data}, 200
