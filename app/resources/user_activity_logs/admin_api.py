import datetime
import calendar

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import load_only
from sqlalchemy import func, distinct, and_,Date, cast, asc, desc, orm
from sqlalchemy.dialects.postgresql import INTERVAL, TIMESTAMP, DATE
from flasgger import swag_from
from werkzeug.exceptions import HTTPException
from flask_restful import abort
from flask import current_app, request, g

from app.base.api import AuthResource
from app.auth.decorators import role_permission_required
from app import c_abort, db
from app.resources.user_activity_logs.models import UserActivityLog
from app.resources.user_activity_logs.schemas import (
    UserActivityLogSchema, UserActivityLogReadArgsSchema,
    UserActivityTimewiseArgsSchema, UserActivityTimewiseSchema,
    UserActivityRecordSchema, UserActivityRecordReadArgSchema)
from app.resources.roles import constants as ROLE
from app.resources.user_activity_logs import constants as UACTLOG
from app.domain_resources.domains.helpers import (
    get_domain_name, get_domain_info)
from app.resources.users.models import User
from app.resources.user_profiles.models import UserProfile
from app.resources.accounts.models import Account
from sqlalchemy import extract



class UserActivityLogRecordListAPI(AuthResource):
    """
    Get API for managing corporate access event stats overall
    """
    model_class = UserActivityLog

    def __init__(self, *args, **kwargs):
        super(UserActivityLogRecordListAPI, self).__init__(*args, **kwargs)

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

        if extra_query:
            if 'full_name' in extra_query and extra_query['full_name']:
                full_name = '%' + (extra_query["full_name"]).lower() + '%'
                query_filters['filters'].append(func.concat(
                    func.lower(UserProfile.first_name), ' ',
                    func.lower(UserProfile.last_name)).like(full_name))
            if 'account_name' in extra_query and extra_query['account_name']:
                account_name = '%' + extra_query.pop('account_name') + '%'
                query_filters['filters'].append(
                    func.lower(Account.account_name).like(func.lower(account_name)))

        # add filters in final_filters
        final_filter = []
        if query_filters['filters']:
            if operator == 'and':
                op_fxn = and_
            elif operator == 'or':
                op_fxn = or_
            final_filter.append(op_fxn(*query_filters['filters']))

        user_query = db.session.query(UserActivityLog).with_entities(
            UserActivityLog.user_id).group_by(
            UserActivityLog.user_id).subquery('user_query')

        query = db.session.query(user_query.c.user_id
            ,UserProfile.first_name, UserProfile.last_name,
            UserProfile.designation, Account.account_name).join(
        UserProfile, UserProfile.user_id == user_query.c.user_id).join(
        User, User.row_id == user_query.c.user_id).join(Account,
        Account.row_id == User.account_id)

        if final_filter:
            query = query.filter(and_(*final_filter))

        if sort:
            for col in sort['sort_by']:
                if col == 'created_date':
                    sort_fxn = asc('created_date')
                    if sort['sort'] == 'dsc':
                        sort_fxn = desc('created_date')
                elif col == 'full_name':
                    sort_fxn = asc('first_name')
                    if sort['sort'] == 'dsc':
                        sort_fxn = desc('first_name')
                elif col == 'account_name':
                    sort_fxn = asc('account_name')
                    if sort['sort'] == 'dsc':
                        sort_fxn = desc('account_name')
                elif col == 'designation':
                    sort_fxn = asc('designation')
                    if sort['sort'] == 'dsc':
                        sort_fxn = desc('designation')

        final_query = query.order_by(sort_fxn).paginate(
                paging['page'], paging['per_page'], error_out=False)

        return final_query, db_projection, s_projection

    def get(self):
        """
        Get the list
        """
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            UserActivityRecordReadArgSchema(strict=True))

        try:
            # build the sql query
            query, db_projection, s_projection =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session,
                                 operator)

            # making a copy of the main output schema
            comment_schema = UserActivityRecordSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                comment_schema = UserActivityRecordSchema(
                    only=s_projection)

            # prepare models for output dump
            models = [m for m in query.items]
            total = query.total
            if not models:
                c_abort(404, message='No matching Email logs found')
            result = comment_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class UserActivityLogAPI(AuthResource):
    """
    CRUD API for user activity log
    """

    # @swag_from('swagger_docs/research_report_post.yml')
    def post(self):
        """
        Create user activity log
        """

        user_activity_schema = UserActivityLogSchema()
        # get the form data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            json_data['login_log_id'] = g.current_user['login_log_id']
            json_data['user_id'] = g.current_user['row_id']
            json_data['account_id'] = g.current_user['account_id']

            data, errors = user_activity_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            db.session.add(data)
            db.session.commit()

        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'User activity log created: %s' %
                           str(data.row_id), 'row_id': data.row_id}, 201


class UserActivityLogListAPI(AuthResource):
    """
    Read API for user activity log lists, i.e, more than 1
    """
    model_class = UserActivityLog

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['user', 'account', 'login_log']
        super(UserActivityLogListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        date = None
        if 'created_date' in filters:
            date = filters.pop('created_date')

        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)

        if date:
            query_filters['base'].append(
                cast(UserActivityLog.created_date,Date) == date)

        query = self._build_final_query(
            query_filters, query_session, operator)

        if sort:
            for col in sort['sort_by']:
                if col == 'created_date':
                    sort_fxn = asc('created_date')
                    if sort['sort'] == 'dsc':
                        sort_fxn = desc('created_date')

        query = query.order_by(sort_fxn).paginate(
                paging['page'], paging['per_page'], error_out=False)


        return query, db_projection, s_projection, order, paging

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA])
    @swag_from('swagger_docs/login_logs_getlist.yml')
    def get(self):
        """
        Get the list
        """
        total = 0
        login_log_read_schema = UserActivityLogReadArgsSchema(
            strict=True)
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            login_log_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(UserActivityLog),
                                 operator)
            # making a copy of the main output schema
            user_activity_log_schema = UserActivityLogSchema()

            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                user_activity_log_schema = UserActivityLogSchema(
                    only=s_projection)

            # prepare models for output dump
            models = [m for m in query.items]
            total = query.total
            if not models:
                c_abort(404, message='No matching user activity logs found')

            result = user_activity_log_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class ActionVisitCountAPI(AuthResource):
    """
    Read API for user activity log lists, i.e, more than 1
    """
    model_class = UserActivityLog

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['user', 'account', 'login_log']
        super(ActionVisitCountAPI, self).__init__(*args, **kwargs)

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
        visit_query = query.distinct(func.concat(
            UserActivityLog.user_id, func.cast(
                UserActivityLog.created_date, DATE)))
        return query, visit_query, db_projection, s_projection, order, paging

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA])
    @swag_from('swagger_docs/login_logs_getlist.yml')
    def get(self):
        """
        Get the list
        """
        result = {'actions': 0, 'visits': 0}
        login_log_read_schema = UserActivityLogReadArgsSchema(
            strict=True)
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            login_log_read_schema)
        try:
            # build the sql query
            query, visit_query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(UserActivityLog),
                                 operator)
            result['actions'] = query.count()
            result['visits'] = visit_query.count()

        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class VisitsActionsOverTimeAPI(AuthResource):
    """
    Read API for user activity log lists, i.e, more than 1
    """
    model_class = UserActivityLog

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['user', 'account', 'login_log']
        super(VisitsActionsOverTimeAPI, self).__init__(*args, **kwargs)

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

        time_unit = filters['time_unit']

        activity_log_query = db.session.query(
            UserActivityLog).join(
            Account, Account.row_id == UserActivityLog.account_id
        ).with_entities(Account.domain_id, UserActivityLog.created_date,
            UserActivityLog.row_id, UserActivityLog.user_id).subquery()

        activity_filters = []
        current_utc_time = datetime.datetime.utcnow()
        datetime_formate = "%Y-%m-%d %H:%M:%S"

        if extra_query:
            if 'date' in extra_query :
                if 'day' == time_unit:
                    if (extra_query['date'].year == current_utc_time.year and
                        extra_query['date'].month == current_utc_time.month):
                        current_time = datetime.datetime.strftime(current_utc_time,
                            datetime_formate)
                    else:
                        current_time = (str(extra_query['date'].year)+'-'+
                            str(extra_query['date'].month)+'-'+str(calendar.monthrange(
                            extra_query['date'].year,extra_query['date'].month)[1])+' '+
                            '00:00:00') 
                    start_time = str(str(extra_query['date'].year)+'-'+
                        str(extra_query['date'].month)+'-01 00:00:00')

                    activity_filters.append(and_(
                        func.extract(
                            'year',activity_log_query.c.created_date) == 
                        extra_query['date'].year,
                        func.extract('month',activity_log_query.c.created_date) == 
                        extra_query['date'].month))

                elif 'month' == time_unit:

                    if extra_query['date'].year == current_utc_time.year:
                        current_time = datetime.datetime.strftime(current_utc_time,
                            datetime_formate)
                    else:
                        current_time = str(extra_query['date'].year)+'-12-31 23:59:59'
                    start_time = str(extra_query['date'].year)+'-01-01 00:00:00'

                    activity_filters.append(
                        func.extract('year',activity_log_query.c.created_date) == 
                        extra_query['date'].year)

                else:
                    time_delta = relativedelta(
                        **{UACTLOG.TIMEDELTA_PARAMS[time_unit]:
                            filters['num_of_bars']-1})
                    current_time = datetime.datetime.utcnow()
                    start_time = current_time - time_delta

            else:
                time_delta = relativedelta(
                    **{UACTLOG.TIMEDELTA_PARAMS[time_unit]:
                        filters['num_of_bars']-1})
                current_time = datetime.datetime.utcnow()
                start_time = current_time - time_delta

        else:
            time_delta = relativedelta(
                **{UACTLOG.TIMEDELTA_PARAMS[time_unit]:
                    filters['num_of_bars']-1})
            current_time = datetime.datetime.utcnow()
            start_time = current_time - time_delta

        time_query = db.session.query(
            func.generate_series(
                func.date_trunc(
                    time_unit, func.cast(start_time, TIMESTAMP)),
                func.date_trunc(
                    time_unit, func.cast(current_time, TIMESTAMP)),
                func.cast(
                    "1 {}".format(time_unit), INTERVAL
                )).label('time')).subquery()
        activity_filters.append(and_(time_query.c.time == func.date_trunc(
            time_unit, activity_log_query.c.created_date)))

        domain_code = request.headers.get('DomainCode')
        if domain_code:
            domain_name = get_domain_name(domain_code)
            domain_id, domain_conf = get_domain_info(domain_name)
            activity_filters.append(activity_log_query.c.domain_id == domain_id)
        time_wise_query = db.session.query(
            time_query.c.time.label('time'),
            func.count(activity_log_query.c.id).label('activities'),
            func.count(distinct(func.concat(
                activity_log_query.c.user_id, func.cast(
                    activity_log_query.c.created_date, DATE)))).filter(
                activity_log_query.c.user_id != None).label('visits')
        ).join(activity_log_query, and_(*activity_filters), isouter=True
               ).group_by(time_query.c.time).order_by(time_query.c.time)
        return time_wise_query, db_projection, s_projection, order, paging

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA])
    # @swag_from('swagger_docs/login_logs_getlist.yml')
    def get(self):
        """
        Get the list
        """
        login_log_read_schema = UserActivityTimewiseArgsSchema(
            strict=True)
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            login_log_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(UserActivityLog),
                                 operator)

            result = UserActivityTimewiseSchema().dump(query.all(), many=True)

        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data}, 200
