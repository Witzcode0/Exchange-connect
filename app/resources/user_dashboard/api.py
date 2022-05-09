"""
Api for events calendar
"""
from datetime import timedelta

from flask import current_app, g
from flask_restful import abort
from sqlalchemy import func, and_
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.resources.user_dashboard.schemas import (
    UserDashboardStatsReadArgsSchema, UserDashboardStatsSchema,
    UserEventMonthWiseStatsSchema, UserMonthWiseEventTypeStatsSchema)
from app.corporate_access_resources.corporate_access_events.models import \
    CorporateAccessEvent
from app.corporate_access_resources.ref_event_sub_types.models import \
    CARefEventSubType
from app.resources.contacts.models import Contact
from app.resources.event_calendars.helpers import corporate_query
from app.resources.users.models import User
from app.resources.accounts.models import Account
from app.resources.accounts import constants as ACC
from app.resources.follows.models import CFollow
from app.crm_resources.crm_contacts.models import CRMContact
from app.resources.user_settings.models import UserSettings


class UserDashboardStatsListAPI(AuthResource):
    """
    Get API for managing user dashboard stats
    """

    def __init__(self, *args, **kwargs):
        super(UserDashboardStatsListAPI, self).__init__(*args, **kwargs)

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
        query_filters['base'].append(and_(
            CorporateAccessEvent.cancelled.is_(False),
            CorporateAccessEvent.is_draft.is_(False)))

        event_query = corporate_query(
            filters, query_filters, operator)

        # for count of current user connections group by account type
        # for sent by query
        connection_sent_by_query = db.session.query(
            Contact.row_id.label('row_id'), Contact.sent_to.label('user_id')
            ).filter(Contact.sent_by == g.current_user['row_id'])
        # for sent to query
        connection_sent_to_query = db.session.query(
            Contact.row_id.label('row_id'), Contact.sent_by.label('user_id')
            ).filter(Contact.sent_to == g.current_user['row_id'])
        # union with sent by and sent to query
        connection_sub_query = connection_sent_by_query.union(
            connection_sent_to_query).subquery()
        # Group by account type with count of contact
        total_connection_by_account_type_query = db.session.query(
            Account.account_type.label('account_type'),
            func.count(connection_sub_query.c.row_id).label('total_count')
            ).join(User, Account.row_id == User.account_id).join(
            connection_sub_query, User.row_id == connection_sub_query.c.user_id,
            isouter=True).group_by(Account.account_type).having(and_(
                Account.account_type != ACC.ACCT_GUEST,
                Account.account_type != ACC.ACCT_ADMIN,
                Account.account_type != ACC.ACCT_PRIVATE,
                Account.account_type != ACC.ACCT_SME))
        # total crm contact
        contact = CRMContact.query.filter(
            CRMContact.created_by == g.current_user['row_id']).subquery()
        total_contact_query = db.session.query(
            func.count(contact.c.id).label('total_count'),
            contact.c.contact_type.label('account_type')
            ).group_by(contact.c.contact_type)
        # Group by account type all following company by current_user
        following_company = CFollow.query.filter(
            CFollow.sent_by == g.current_user['row_id']).subquery()
        total_following_company = db.session.query(
            Account.account_type.label('account_type'),
            func.count(following_company.c.id).label('total_count')).join(
            following_company, following_company.c.company_id ==
            Account.row_id, isouter=True).group_by(
            Account.account_type).having(
            and_(Account.account_type != ACC.ACCT_GUEST,
                 Account.account_type != ACC.ACCT_ADMIN,
                 Account.account_type != ACC.ACCT_PRIVATE,
                 Account.account_type != ACC.ACCT_SME,
                 ))

        return event_query, total_connection_by_account_type_query, \
               total_following_company, total_contact_query

    def get(self):
        """
        Get user dashboard stats
        """

        user_dashboard_read_schema = UserDashboardStatsReadArgsSchema()
        user_dashboard_schema = UserDashboardStatsSchema()

        filters, pfields, sort, pagination, operator = self.parse_args(
            user_dashboard_read_schema)

        try:
            # build the sql query
            event_total_count = {}
            event_count_query, total_connection_by_account_type_query, \
                total_following_company, total_contact_query = \
                self.build_query(
                    filters, pfields, sort, pagination, db.session.query(
                        CorporateAccessEvent), operator)
            connection_counts = total_connection_by_account_type_query.all()
            event_count = event_count_query.all()
            following_company = total_following_company.all()
            contact_counts = total_contact_query.all()

            event_total_count['total_events'] = len(event_count)
            result = user_dashboard_schema.dump(event_total_count)

            result.data['total_connection_by_account_type'] = \
                user_dashboard_schema.dump(connection_counts, many=True).data
            result.data['total_connections'] = sum(
                [c.total_count for c in connection_counts])
            result.data['total_contact_by_account_type'] = \
                user_dashboard_schema.dump(contact_counts, many=True).data
            result.data['total_contacts'] = sum(
                [c.total_count for c in contact_counts])
            result.data['total_following_company_by_account_type'] = \
                user_dashboard_schema.dump(following_company, many=True).data
            result.data['total_following'] = sum(
                [c.total_count for c in following_company])
            included_ac_types = [c_cnt[1] for c_cnt in contact_counts]
            for ac_type in ACC.CRM_ACCT_TYPES:
                if ac_type in (ACC.ACCT_GUEST, ACC.ACCT_SME, ACC.ACCT_PRIVATE):
                    continue
                if ac_type not in included_ac_types:
                        result.data['total_contact_by_account_type'].append(
                            {'account_type':ac_type,
                             'total_count': 0})
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'result': result.data}, 200


class UserEventMonthWiseStatsListAPI(AuthResource):
    """
    Get API for managing user event wise stats
    """

    def __init__(self, *args, **kwargs):
        super(UserEventMonthWiseStatsListAPI, self).__init__(*args, **kwargs)

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
            pass

        query_filters['base'].append(and_(
            CorporateAccessEvent.cancelled.is_(False),
            CorporateAccessEvent.is_draft.is_(False)))

        event_query = corporate_query(
            filters, query_filters, operator)

        event_sub_query = event_query.subquery()
        setting = UserSettings.query.filter_by(
            user_id=g.current_user['row_id']).first()
        user_timezone = current_app.config['USER_DEFAULT_TIMEZONE']
        if setting and setting.timezone:
            user_timezone = setting.timezone
        start_date_col = func.timezone(
            user_timezone, func.timezone(
                'UTC', event_sub_query.c.start_date))
        month_query = db.session.query(
            func.generate_series(1, 12, 1).label('month')).subquery()
        event_month_wise_query = db.session.query(
            month_query.c.month.label(
                'month'), func.count(event_sub_query.c.row_id).label(
                'count')).join(
            event_sub_query, month_query.c.month == func.extract(
                'month', start_date_col), isouter=True).group_by(
            month_query.c.month).order_by(month_query.c.month)
        return event_month_wise_query

    def get(self):
        """
        Get user dashboard stats
        """

        user_dashboard_read_schema = UserDashboardStatsReadArgsSchema()

        filters, pfields, sort, pagination, operator = self.parse_args(
            user_dashboard_read_schema)

        try:
            # build the sql query
            event_total_count = {}
            event_month_wise_query = self.build_query(
                filters, pfields, sort, pagination, db.session.query(
                    CorporateAccessEvent), operator)
            contact_counts = event_month_wise_query.all()
            result = UserEventMonthWiseStatsSchema().dump(
                contact_counts, many=True)
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'result': result.data}, 200


class UserMonthWiseEventTypeStatsListAPI(AuthResource):
    """
    Get API for managing user event wise stats
    """

    def __init__(self, *args, **kwargs):
        super(UserMonthWiseEventTypeStatsListAPI, self).__init__(
            *args, **kwargs)

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
            pass

        query_filters['base'].append(and_(
            CorporateAccessEvent.cancelled.is_(False),
            CorporateAccessEvent.is_draft.is_(False)))

        event_query = corporate_query(
            filters, query_filters, operator)
        event_sub_query = event_query.subquery()
        event_type_wise_query = db.session.query(
            CARefEventSubType.name.label('event_type_name'),
            func.count(event_sub_query.c.row_id).label('count')).join(
            event_sub_query, CARefEventSubType.row_id ==
            event_sub_query.c.event_type_id, isouter=True).\
            filter(CARefEventSubType.deleted == False).\
            group_by('event_type_name')

        return event_type_wise_query

    def get(self):
        """
        Get user dashboard stats
        """

        user_dashboard_read_schema = UserDashboardStatsReadArgsSchema()

        filters, pfields, sort, pagination, operator = self.parse_args(
            user_dashboard_read_schema)

        try:
            # build the sql query
            event_total_count = {}
            event_type_wise_query = self.build_query(
                filters, pfields, sort, pagination, db.session.query(
                    CorporateAccessEvent), operator)
            event_type_counts = event_type_wise_query.all()
            result = UserMonthWiseEventTypeStatsSchema().dump(
                event_type_counts, many=True)
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'result': result.data}, 200
