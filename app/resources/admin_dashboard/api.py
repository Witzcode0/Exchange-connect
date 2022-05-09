from werkzeug.exceptions import Forbidden, HTTPException
from flask import current_app
from flask_restful import abort
from sqlalchemy import and_
from sqlalchemy.sql import func, case
from flasgger.utils import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.auth.decorators import role_permission_required
from app.resources.users.models import User
from app.resources.accounts.models import Account
from app.resources.roles import constants as ROLE
from app.webinar_resources.webinars.models import Webinar
from app.webcast_resources.webcasts.models import Webcast
from app.toolkit_resources.projects.models import Project
from app.toolkit_resources.ref_project_types.models import RefProjectType
from app.corporate_access_resources.ca_open_meetings.models import\
    CAOpenMeeting
from app.corporate_access_resources.corporate_access_events.models import\
    CorporateAccessEvent
from app.resources.admin_dashboard.schemas import (
    AdminDashboardStatsSchema, AdminDashboardStatsReadArgsSchema,
    TotalUserByTypeSchema, TotalAccountByTypeSchema, TotalWebinarByTypeSchema,
    TotalWebcastByTypeSchema, TotalProjectByTypeSchema,
    TotalMeetingByTypeSchema, TotalCAEventByTypeSchema)
from app.resources.accounts import constants as ACCT


class AdminDashboardStatsListAPI(AuthResource):
    """
    Get API for managing admin dashboard stats
    """

    def __init__(self, *args, **kwargs):
        super(AdminDashboardStatsListAPI, self).__init__(
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

        # build specific extra queries filters
        if extra_query:
            pass

        query_user = db.session.query(
            User.account_type, func.count(case(
                [(User.deactivated.is_(False), 0)])).label(
                'active_user_count'), func.count(
                case([(User.deactivated, 0)])).label(
                'deactivated_user_count')).filter(
            User.account_type.notin_((ACCT.ACCT_SME, ACCT.ACCT_PRIVATE))
            ).group_by(User.account_type)
        query_user = self._build_final_query(
            query_filters, query_user, operator, main_class=User)

        query_account = db.session.query(
            Account.account_type, func.count(case(
                [(Account.activation_date.isnot(None), 0)])).label(
                'active_account_count'), func.count(
                case([(Account.activation_date.is_(None), 0)])).label(
                'deactivated_account_count')).filter(
            Account.account_type.notin_((
                ACCT.ACCT_SME, ACCT.ACCT_PRIVATE, ACCT.ACCT_GUEST))
            ).group_by(Account.account_type)
        query_account = self._build_final_query(
            query_filters, query_account, operator, main_class=Account)

        query_group_webinar_draft_type = db.session.query(
            Account.account_type.label('account_type'),
            func.count(Webinar.row_id).label('total_webinar_count')
            ).join(Webinar, and_(
                Account.row_id == Webinar.account_id,
                Webinar.is_draft.is_(False)), isouter=True).filter(
            Account.account_type.notin_((ACCT.ACCT_SME, ACCT.ACCT_PRIVATE))
            ).group_by(
            Account.account_type)
        query_group_webinar_draft_type = self._build_final_query(
            query_filters, query_group_webinar_draft_type, operator,
            main_class=Account)

        query_group_project_draft_type = db.session.query(
            func.count(Project.row_id).label('total_project_count'),
            RefProjectType.project_type_name.label('project_type_name')).join(
            RefProjectType, RefProjectType.row_id ==
            Project.project_type_id).filter(
            Project.is_draft == False).group_by(
                RefProjectType.project_type_name)
        query_group_project_draft_type = self._build_final_query(
            query_filters, query_group_project_draft_type, operator,
            main_class=Project)

        query_group_webcast_draft_type = db.session.query(
            Account.account_type.label('account_type'),
            func.count(Webcast.row_id).label('total_webcast_count'),
            ).join(Webcast, and_(
                Account.row_id == Webcast.account_id,
                Webcast.is_draft.is_(False)), isouter=True
            ).filter(
                Account.account_type.notin_((ACCT.ACCT_SME, ACCT.ACCT_PRIVATE))
            ).group_by(Account.account_type)
        query_group_webcast_draft_type = self._build_final_query(
            query_filters, query_group_webcast_draft_type, operator, main_class=Account)

        query_group_meeting_type = db.session.query(
            Account.account_type.label('account_type'),
            func.count(CAOpenMeeting.row_id).label('total_meeting_count'),
            ).join(CAOpenMeeting, and_(
                Account.row_id == CAOpenMeeting.account_id,
                CAOpenMeeting.is_draft.is_(False)), isouter=True
           ).filter(
                Account.account_type.notin_((ACCT.ACCT_SME, ACCT.ACCT_PRIVATE))
            ).group_by(Account.account_type)
        query_group_meeting_type = self._build_final_query(
            query_filters, query_group_meeting_type, operator, main_class=Account)

        query_group_ca_event_type = db.session.query(
            Account.account_type.label('account_type'),
            func.count(CorporateAccessEvent.row_id).label(
                'total_ca_event_count'), ).join(CorporateAccessEvent, and_(
                    Account.row_id == CorporateAccessEvent.account_id,
                    CorporateAccessEvent.is_draft.is_(False)),
            isouter=True).filter(
            Account.account_type.notin_((ACCT.ACCT_SME, ACCT.ACCT_PRIVATE))
            ).group_by(Account.account_type)
        query_group_ca_event_type = self._build_final_query(
            query_filters, query_group_ca_event_type, operator,
            main_class=Account)

        return query_user, query_account, \
            query_group_webinar_draft_type, query_group_project_draft_type,\
            query_group_webcast_draft_type, query_group_meeting_type,\
            query_group_ca_event_type

    @role_permission_required(perms=[ROLE.EPT_AA])
    @swag_from('swagger_docs/admin_dashboard_stats_get_list.yml')
    def get(self):
        """
        Get admin dashboard stats
        """
        # making a copy of the main output schema
        admin_dashboard_stats_schema = AdminDashboardStatsSchema()

        admin_dashboard_read_stats_schema = AdminDashboardStatsReadArgsSchema()

        filters, pfields, sort, pagination, operator = self.parse_args(
            admin_dashboard_read_stats_schema)
        try:
            # build the sql query
            (query_user, query_account, query_group_webinar_draft_type,
             query_group_project_draft_type, query_group_webcast_draft_type,
             query_group_meeting_type,
             query_group_ca_event_type) = self.build_query(
                filters, pfields, sort, pagination, db.session.query(User),
                operator)

            # run the count query
            count_model = query_user
            # run the group by user type query
            query_user_model = query_user.all()
            # query_deactivated_user_model = query_deactivated_user.all()
            # run the group by account type query
            group_active_account_model = query_account.all()
            # run the group by account type webinar query
            group_webinar_model = query_group_webinar_draft_type.all()
            # run the group by account type project query
            group_project_model = query_group_project_draft_type.all()
            # run the group by account type webcast query
            group_webcast_model = query_group_webcast_draft_type.all()
            # run the group by account type meeting query
            group_meeting_model = query_group_meeting_type.all()
            # run the group by account type ca_event query
            group_ca_event_model = query_group_ca_event_type.all()
            if not count_model:
                c_abort(404, message='No matching stats found')

            # dump the results
            result = admin_dashboard_stats_schema.dump(count_model)

            # combine the group by user type result
            result.data['total_users_by_types'] =\
                TotalUserByTypeSchema().dump(
                    query_user_model, many=True).data
            result.data['total_users'] = 0
            result.data['total_active_users'] = 0
            result.data['total_deactive_users'] = 0
            for ac in result.data['total_users_by_types']:
                result.data['total_active_users'] += ac['active_user_count']
                result.data['total_deactive_users'] += ac[
                    'deactivated_user_count']
            result.data['total_users'] = (result.data['total_active_users'] +
                                          result.data['total_deactive_users'])

            # combine the group by account type result
            result.data['total_account_by_types'] =\
                TotalAccountByTypeSchema().dump(
                    group_active_account_model, many=True).data
            result.data['total_accounts'] = 0
            result.data['total_active_accounts'] = 0
            result.data['total_deactive_accounts'] = 0
            for ac in result.data['total_account_by_types']:
                result.data['total_active_accounts'] += ac[
                    'active_account_count']
                result.data['total_deactive_accounts'] += ac[
                    'deactivated_account_count']
            result.data['total_accounts'] = (
                result.data['total_active_accounts'] +
                result.data['total_deactive_accounts'])

            # combine the group by webinar type result
            result.data['total_webinar_by_types'] =\
                TotalWebinarByTypeSchema().dump(
                    group_webinar_model, many=True).data
            result.data['total_webinars'] = 0
            for ac in result.data['total_webinar_by_types']:
                result.data['total_webinars'] += ac['total_webinar_count']

            # combine the group by project type result
            result.data['total_project_by_types'] =\
                TotalProjectByTypeSchema().dump(
                    group_project_model, many=True).data
            result.data['total_projects'] = 0
            for ac in result.data['total_project_by_types']:
                result.data['total_projects'] += ac['total_project_count']

            # combine the group by webcast type result
            result.data['total_webcast_by_types'] =\
                TotalWebcastByTypeSchema().dump(
                    group_webcast_model, many=True).data
            result.data['total_webcasts'] = 0
            for ac in result.data['total_webcast_by_types']:
                result.data['total_webcasts'] += ac['total_webcast_count']

            # combine the group by meeting type result
            result.data['total_meeting_by_types'] =\
                TotalMeetingByTypeSchema().dump(
                    group_meeting_model, many=True).data
            result.data['total_meetings'] = 0
            for ac in result.data['total_meeting_by_types']:
                result.data['total_meetings'] += ac['total_meeting_count']

            # combine the group by ca_event type result
            result.data['total_ca_event_by_types'] =\
                TotalCAEventByTypeSchema().dump(
                    group_ca_event_model, many=True).data
            result.data['total_ca_events'] = 0
            for ac in result.data['total_ca_event_by_types']:
                result.data['total_ca_events'] += ac['total_ca_event_count']

        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data}, 200
