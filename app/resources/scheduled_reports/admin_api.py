from sqlalchemy.orm import load_only, aliased
from sqlalchemy import func, and_, or_
from werkzeug.exceptions import HTTPException
from flask import current_app, request
from flask_restful import abort
from flasgger import swag_from

from app import db, c_abort
from app.auth.decorators import role_permission_required
from app.base.api import AuthResource
from app.resources.roles import constants as ROLE
from app.resources.scheduled_reports.models import (
    ScheduledReport, ScheduledReportLog)
from app.resources.users.models import User
from app.resources.accounts.models import Account
from app.resources.user_profiles.models import UserProfile
from app.resources.scheduled_reports.schemas import (
    AdminScheduledReportReadArgsSchema, AdminScheduledReportSchema,
    ScheduledReportsUserwiseSchema, ScheduledReportsUserwiseReadArgsSchema,
    AdminScheduledReportLogReadArgsSchema,
    ScheduledReportLogSchema)
from app.domain_resources.domains.helpers import (
    get_domain_info, get_domain_name)


class AdminScheduledReportListAPI(AuthResource):
    """
    Read API for scheduled report lists, i.e, more than 1
    """
    model_class = ScheduledReport

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['creator']
        super(AdminScheduledReportListAPI, self).__init__(*args, **kwargs)

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
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    @swag_from('swagger_docs/admin_scheduled_report_getlist.yml')
    def get(self):
        """
        Get the list
        """
        total = 0
        scheduled_report_read_schema = AdminScheduledReportReadArgsSchema(
            strict=True)

        try:
            # parse the request query arguments
            filters, pfields, sort, pagination, operator = self.parse_args(
                scheduled_report_read_schema)
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(ScheduledReport),
                                 operator, True)
            # making a copy of the main output schema
            scheduled_report_schema = AdminScheduledReportSchema(
                exclude=AdminScheduledReportSchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                scheduled_report_schema = AdminScheduledReportSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching scheduled reports found')

            result = scheduled_report_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class AdminScheduledReportUserwiseAPI(AuthResource):
    """
    Read API for scheduled report lists, i.e, more than 1
    """

    model_class = User

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """

        account_name = filters.get('account_name')
        full_name = filters.get('full_name')
        email = filters.get('email')
        extra_filters = []
        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)
        user = aliased(User, name='user')

        query = db.session.query(user, func.count(
            ScheduledReport.row_id).label('count')).join(
            ScheduledReport,
            ScheduledReport.created_by == user.row_id).join(
                UserProfile, UserProfile.user_id == user.row_id).join(
                Account, user.account_id == Account.row_id).group_by(
            user.row_id)
        if full_name:
            full_name = "%" + extra_query['full_name'].lower() + "%"
            extra_filters.append(func.concat(
                    func.lower(UserProfile.first_name), ' ',
                    func.lower(UserProfile.last_name)).like(full_name))
        if account_name:
            account_name = "%" + account_name.lower() + "%"
            extra_filters.append(func.lower(
                Account.account_name).like(account_name))
        if email:
            email = "%" + email.lower() + "%"
            extra_filters.append(func.lower(
                user.email).like(email))
        if 'Domain-Code' in request.headers:
            domain_name = get_domain_name(request.headers['Domain-Code'])
            domain_id, domain_config = get_domain_info(domain_name)
            query = query.filter(Account.domain_id == domain_id)

        if extra_filters:
            if operator == 'and':
                op_fxn = and_
            elif operator == 'or':
                op_fxn = or_
            query = query.filter(op_fxn(*extra_filters))

        return query, db_projection, s_projection, order, paging

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    @swag_from('swagger_docs/admin_scheduled_report_userwise_getlist.yml')
    def get(self):
        """
        Get the list
        :return:
        """
        total = 0
        read_arg_schema = ScheduledReportsUserwiseReadArgsSchema(strict=True)
        try:
            # parse the request query arguments
            filters, pfields, sort, pagination, operator = self.parse_args(
                read_arg_schema)
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(ScheduledReport),
                                 operator)
            # making a copy of the main output schema
            user_wise_schema = ScheduledReportsUserwiseSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                user_wise_schema = ScheduledReportsUserwiseSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order)
            full_query = full_query.paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching scheduled reports found')

            result = user_wise_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data, 'total': total}, 200


class AdminScheduledReportLogListAPI(AuthResource):
    """
    Read API for scheduled report lists, i.e, more than 1
    """
    model_class = ScheduledReportLog

    def __init__(self, *args, **kwargs):
        # kwargs['special_fields'] = ['creator']
        super(AdminScheduledReportLogListAPI, self).__init__(*args, **kwargs)

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
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    @swag_from('swagger_docs/admin_scheduled_report_log_getlist.yml')
    def get(self):
        """
        Get the list
        """
        total = 0
        s_report_log_read_schema = AdminScheduledReportLogReadArgsSchema(
            strict=True)

        try:
            # parse the request query arguments
            filters, pfields, sort, pagination, operator = self.parse_args(
                s_report_log_read_schema)
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(ScheduledReportLog),
                                 operator)
            # making a copy of the main output schema
            report_log_schema = ScheduledReportLogSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                report_log_schema = ScheduledReportLogSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching scheduled report logs found')

            result = report_log_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
