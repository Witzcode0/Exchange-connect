"""
API endpoints for "corporate access event slots" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import current_app, g
from flask_restful import abort
from sqlalchemy.orm import load_only
from sqlalchemy.sql import func
from flasgger.utils import swag_from
from sqlalchemy import cast, DECIMAL
from sqlalchemy.sql.functions import coalesce
from sqlalchemy import and_, or_, distinct, any_
from sqlalchemy.inspection import inspect

from app import db, c_abort
from app.base.api import AuthResource
from app.resources.users.models import User
from app.corporate_access_resources.ref_event_sub_types.models import \
    CARefEventSubType
from app.corporate_access_resources.corporate_access_events.models import \
    CorporateAccessEvent
from app.corporate_access_resources.corporate_access_event_attendees.models \
    import CorporateAccessEventAttendee
from app.corporate_access_resources.corporate_access_event_stats.models \
    import CorporateAccessEventStats
from app.corporate_access_resources.corporate_access_event_stats.schemas \
    import (CorporateAccessEventStatsSchema,
            CorporateAccessEventStatsReadArgsSchema,
            CorporateAccessEventStatsOverallSchema, CAESTotalEventByTypeSchema,
            CAESTotalAttendeeByTypeSchema,
            CorporateAccessEventStatsOverallReadArgsSchema)
from app.resources.accounts import constants as ACCT
from app.corporate_access_resources.corporate_access_event_inquiries.models \
    import CorporateAccessEventInquiry
from app.corporate_access_resources.corporate_access_event_participants.models \
    import CorporateAccessEventParticipant
from app.corporate_access_resources.corporate_access_event_hosts.models \
    import CorporateAccessEventHost
from app.corporate_access_resources.corporate_access_event_invitees.models \
    import CorporateAccessEventInvitee
from app.corporate_access_resources.corporate_access_event_collaborators.models \
    import CorporateAccessEventCollaborator
from app.resources.event_calendars.helpers import corporate_query


class CorporateAccessEventStatsAPI(AuthResource):
    """
    CRUD API for managing corporate access event stats
    """

    @swag_from('swagger_docs/corporate_access_event_stats_get.yml')
    def get(self, row_id):
        """
        Get a corporate access event stats by id
        """
        corp_access_event_stats_schema = CorporateAccessEventStatsSchema()
        model = None
        try:
            # first find model
            model = CorporateAccessEventStats.query.get(row_id)
            if model is None:
                c_abort(404, message='Corporate Access Event Stats id: %s'
                        ' does not exist' % str(row_id))
            result = corp_access_event_stats_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class CorporateAccessEventStatsListAPI(AuthResource):
    """
    Read API for corporate access event stats list,
    i.e, more than 1 corporate access event stats
    """
    model_class = CorporateAccessEventStats

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['corporate_access_event',
                                    'account', 'creator']
        super(CorporateAccessEventStatsListAPI, self).__init__(*args, **kwargs)

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

    @swag_from('swagger_docs/corporate_access_event_stats_get_list.yml')
    def get(self):
        """
        Get the list
        """
        corp_access_event_stats_read_schema = \
            CorporateAccessEventStatsReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            corp_access_event_stats_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(CorporateAccessEventStats),
                                 operator)
            # making a copy of the main output schema
            corp_access_event_stats_schema = CorporateAccessEventStatsSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                corp_access_event_stats_schema = \
                    CorporateAccessEventStatsSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching corporate'
                        ' access event stats found')
            result = corp_access_event_stats_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class CorporateAccessEventStatsOverallAPI(AuthResource):
    """
    Get API for managing corporate access event stats overall
    """
    model_class = CorporateAccessEvent

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['corporate_access_event',
                                    'account', 'creator']
        super(CorporateAccessEventStatsOverallAPI, self).__init__(
            *args, **kwargs)

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

        # test code
        query_filters['base'] = [and_(
            CorporateAccessEvent.cancelled.is_(False),
            CorporateAccessEvent.is_draft.is_(False))]
        final_query = corporate_query(
            filters, query_filters, operator)

        subquery = final_query.subquery()
        query = db.session.query(
            func.count(distinct(subquery.c.row_id)).label('total_events'),
            func.count(distinct(subquery.c.city)).label('total_location'),
            func.count(subquery.c.attended).label('total_attended'),
            func.count(subquery.c.invited).label('total_invited'),
            func.count(subquery.c.hosted).label('total_hosted'),
            func.count(subquery.c.participated).label('total_participated'),
            func.count(subquery.c.collaborated).label('total_collaborated'),)
        # group by event type query
        query_group_event_type = db.session.query(
            func.count(CorporateAccessEvent.row_id).label(
                'total'), CARefEventSubType.name.label('name')).join(
            CARefEventSubType,
            CorporateAccessEvent.event_sub_type_id ==
            CARefEventSubType.row_id).group_by(CARefEventSubType.row_id)
        query_group_event_type = self._build_final_query(
            query_filters, query_group_event_type, operator)

        # group by account_type stat
        query_group_account_type = db.session.query(
            func.count(CorporateAccessEventAttendee.row_id).label(
                'total'), User.account_type.label('account_type')).filter(
                User.account_type.notin_((ACCT.ACCT_SME, ACCT.ACCT_PRIVATE))
            ).join(
            User,
            User.row_id == CorporateAccessEventAttendee.attendee_id).join(
            CorporateAccessEvent,
            CorporateAccessEvent.row_id ==
            CorporateAccessEventAttendee.corporate_access_event_id).group_by(
                User.account_type)
        query_group_account_type = self._build_final_query(
            query_filters, query_group_account_type, operator)

        return query, query_group_event_type, query_group_account_type

    @swag_from('swagger_docs/corporate_access_event_global_stats_get_list.yml')
    def get(self):
        """
        Get corporate access event stats overall
        """
        # making a copy of the main output schema
        corp_access_event_stats_overall_schema = \
            CorporateAccessEventStatsOverallSchema()
        corporate_access_event_stats_overall_read_schema = \
            CorporateAccessEventStatsOverallReadArgsSchema(strict=True)
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            corporate_access_event_stats_overall_read_schema)
        try:
            # build the sql query
            query, query_group_event_type, query_group_account_type =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(CorporateAccessEventStats),
                                 operator)
            # run the count query
            count_model = query.first()
            # run the group by event type query
            group_event_model = query_group_event_type.all()
            # run the group by account type query
            group_account_type_model = query_group_account_type.all()
            if not count_model:
                c_abort(404, message='No matching corporate access'
                        ' event stats found')

            # dump the results
            result = corp_access_event_stats_overall_schema.dump(count_model)
            # combine the group by event result
            result.data['total_events_by_event_sub_types'] =\
                CAESTotalEventByTypeSchema().dump(
                    group_event_model, many=True).data
            # combine the group by account type result
            result.data['total_attendees_by_account_types'] =\
                CAESTotalAttendeeByTypeSchema().dump(
                    group_account_type_model, many=True).data
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data}, 200

