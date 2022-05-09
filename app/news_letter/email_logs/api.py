"""
API endpoints for "email log" package.
"""
import os
import pandas as pd
import datetime
import sqlalchemy as sa

from sqlalchemy.dialects.postgresql import DATE
from sqlalchemy.sql import select
from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.orm import load_only, joinedload
from sqlalchemy import Date, cast, func, case, asc, desc
from sqlalchemy.exc import IntegrityError
from marshmallow.exceptions import ValidationError
from sqlalchemy import and_, any_, or_
from sqlalchemy.inspection import inspect

from app.resources.users.models import User
from app.resources.user_profiles.models import UserProfile
from app.resources.accounts.models import Account
from app.news_letter.distribution_list.models import DistributionList
from app.base import constants as APP
from app import db, c_abort, distributionlistfile
from app.base.api import AuthResource
from app.news_letter.email_logs.models import Emaillogs
from app.news_letter.email_logs.schemas import (
    EmailLogSchema,
    EmailLogReadArgsSchema,
    EmailLogcountSchema,
    EmailLogCountReadArgsSchema)
from app.news_letter.email_logs import constants as CHOICE


class EmailRecordcount(AuthResource):
    """
    Get API for managing corporate access event stats overall
    """
    model_class = Emaillogs

    def __init__(self, *args, **kwargs):
        super(EmailRecordcount, self).__init__(*args, **kwargs)

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
            if "started_at_from" in extra_query and extra_query['started_at_from']:
                started_at = extra_query.pop('started_at_from')
                query_filters['filters'].append(
                    func.cast(Emaillogs.created_date,Date) >= started_at)
            if "ended_at_to" in extra_query and extra_query['ended_at_to']:
                ended_to = extra_query.pop('ended_at_to')
                query_filters['filters'].append(
                    func.cast(Emaillogs.created_date,Date) <= ended_to)

        # add filters in final_filters
        final_filter = []
        if query_filters['filters']:
            if operator == 'and':
                op_fxn = and_
            elif operator == 'or':
                op_fxn = or_
            final_filter.append(op_fxn(*query_filters['filters']))

        user_query = db.session.query(
                    func.cast(Emaillogs.created_date, Date).label("created_date"),
                    func.count(Emaillogs.row_id).label("total"),
                    func.count(case(
                    [(Emaillogs.email_sent == CHOICE.SENT, 1)])).label(
                    'total_sent'),
                    func.count(case(
                    [(Emaillogs.email_sent == CHOICE.NOT_SENT, 0)])).label(
                    'total_notsend'),
                    func.count(case(
                    [(Emaillogs.email_sent == CHOICE.UNSUBSCRIBE, 0)])).label(
                    'total_unsubscribe')).group_by(func.cast(Emaillogs.created_date, Date)
                    )

        if final_filter:
            user_query = user_query.filter(and_(*final_filter))

        if sort:
            for col in sort['sort_by']:
                if col == 'created_date':
                    sort_fxn = asc('created_date')
                    if sort['sort'] == 'dsc':
                        sort_fxn = desc('created_date')

        final_query = user_query.order_by(sort_fxn).paginate(
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
            EmailLogCountReadArgsSchema(strict=True))

        try:
            # build the sql query
            query, db_projection, s_projection =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session,
                                 operator)

            # making a copy of the main output schema
            comment_schema = EmailLogcountSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                comment_schema = EmailLogcountSchema(
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


class EmailLogListAPI(AuthResource):
    """
    Read API for Email Logs, i.e, more than 1
    """
    model_class = Emaillogs

    def __init__(self, *args, **kwargs):
        super(EmailLogListAPI, self).__init__(*args, **kwargs)

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
        
        # build specific extra queries filters
        query_filters_union = {}
        query_filters_union['base'] = query_filters['base'][:]
        query_filters_union['filters'] = query_filters['filters'][:]
        if extra_query:
            if 'account_name' in extra_query and extra_query['account_name']:
                account_name = '%' + extra_query.pop('account_name') + '%'
                query_filters['filters'].append(
                func.lower(Account.account_name).like(func.lower(account_name)))
                query_filters_union['filters'].append(
                func.lower(Account.account_name).like(func.lower(account_name)))
            if 'full_name' in extra_query and extra_query['full_name']:
                full_name = '%' + (extra_query["full_name"]).lower() + '%'
                query_filters['filters'].append(func.concat(
                    func.lower(UserProfile.first_name), ' ',
                    func.lower(UserProfile.last_name)).like(full_name))
                query_filters_union['filters'].append(func.concat(
                    func.lower(DistributionList.first_name), ' ',
                    func.lower(DistributionList.last_name)).like(full_name))

        if date:
            query_filters['base'].append(
                cast(Emaillogs.created_date,Date) == date)
            query_filters_union['base'].append(
                cast(Emaillogs.created_date,Date) == date)

        query = self._build_final_query(
            query_filters, query_session, operator)

        query_for_union = self._build_final_query(
            query_filters_union, query_session, operator)

        # query for user
        user_query = query.join(
            User, User.row_id == Emaillogs.user_id).join(
            Account, Account.row_id == User.account_id).join(
            UserProfile, UserProfile.user_id == User.row_id).with_entities(
            Emaillogs.created_date,
            User.email.label("email"),
            Account.account_name.label("account_name"),
            UserProfile.first_name.label("first_name"),
            UserProfile.last_name.label("last_name"),
            UserProfile.designation.label("designation"),
            Emaillogs.email_sent.label("email_sent"))
        
        # query for distribution user
        dist_user_query = query_for_union.join(
            DistributionList, DistributionList.row_id == Emaillogs.dist_user_id
            ).join(Account, 
            Account.row_id == DistributionList.account_id).with_entities(
            Emaillogs.created_date,
            DistributionList.email.label("email"),
            Account.account_name.label("account_name"),
            DistributionList.first_name.label("first_name"),
            DistributionList.last_name.label("last_name"),
            DistributionList.designation.label("designation"),
            Emaillogs.email_sent.label("email_sent"))

        # merge user and distribution user query
        query = user_query.union(dist_user_query)

        if sort:
            for col in sort['sort_by']:
                if col == 'full_name':
                    mapper = inspect(UserProfile)
                    col = 'first_name'
                    sort_fxn = 'asc'
                    if sort['sort'] == 'dsc':
                        sort_fxn = 'desc'
                    order.append(getattr(mapper.columns[col], sort_fxn)())

                if col == 'account_name':
                    mapper = inspect(Account)
                    col = 'account_name'
                    sort_fxn = 'asc'
                    if sort['sort'] == 'dsc':
                        sort_fxn = 'desc'
                    order.append(getattr(mapper.columns[col], sort_fxn)())
        try:
            final_query = query.order_by(*order).paginate(
                    paging['page'], paging['per_page'], error_out=False)
        except Exception as e:
            current_app.logger.exception(e)
            c_abort(404, message='invalid parameters set')
        
        return final_query, db_projection, s_projection

    def get(self):
        """
        Get the list
        """
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            EmailLogReadArgsSchema(strict=True))
        try:
            # build the sql query
            query, db_projection, s_projection =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Emaillogs),
                                 operator)

            # making a copy of the main output schema
            comment_schema = EmailLogSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                comment_schema = EmailLogSchema(
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
            c_abort(403, message='Not allowed, User has not given '
                            'permission')
        return {'results': result.data, 'total': total}, 200