"""
API endpoints for "follows" package.
"""

from werkzeug.exceptions import HTTPException
from flask import current_app, request, g
from flask_restful import abort
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import load_only, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.base import constants as APP
from app.resources.accounts.models import Account
from app.resources.account_profiles.models import AccountProfile
from app.resources.users.models import User
from app.resources.users import constants as USER
from app.resources.designations.models import Designation
from app.resources.user_profiles.models import UserProfile
from app.resources.follows.models import CFollow
from app.resources.follows.schemas import (
    CFollowHistorySchema, CFollowReadArgsSchema, CFollowSchema, account_fields,
    CFollowAnalysisSchema)
from app.resources.follows.helpers import check_company_follow_exists
from app.resources.follows import constants as CFOLLOW

from queueapp.notification_tasks import add_follow_notification
from queueapp.user_stats_tasks import manage_users_stats


class CFollowAPI(AuthResource):
    """
    Create and Delete CFollow
    """

    @swag_from('swagger_docs/follow_post.yml')
    def post(self):
        """
        Follow a company (account)
        """
        follow_schema = CFollowSchema()
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = follow_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            data.sent_by = g.current_user['row_id']
            # check if 'sent_by' and 'company_id' already exists
            errors = check_company_follow_exists(data)
            if errors:
                c_abort(422, errors={'company_id': [errors]})

            db.session.add(data)
            db.session.commit()
            # TODO :- Use in Future
            # add notification for company users
            add_follow_notification.s(True, data.row_id).delay()
            # update user total_companies
            manage_users_stats.s(
                True, data.sent_by, USER.USR_COMPS).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (company_id)=(10) is not present in table "account".
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'CFollow added %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @swag_from('swagger_docs/follow_delete.yml')
    def delete(self, row_id):
        """
        Delete follow by follower
        """
        follow_history_schema = CFollowHistorySchema()
        model = None
        try:
            model = CFollow.query.get(row_id)
            if model is None:
                c_abort(404, message='CFollow id: %s does not exist' %
                                     str(row_id))
            if model.sent_by == g.current_user['row_id']:
                follow_history = {}
                follow_history['sent_by'] = model.sent_by
                follow_history['company_id'] = model.company_id
                follow_history_data, errors = follow_history_schema.load(
                    follow_history)
                if errors:
                    c_abort(422, errors=errors)
                db.session.add(follow_history_data)
                db.session.delete(model)
                db.session.commit()
                # update user total_companies
                manage_users_stats.s(
                    True, model.sent_by, USER.USR_COMPS,
                    increase=False).delay()
            else:
                c_abort(401)
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'CFollow deleted %s' % str(row_id)}, 204


class CFollowListAPI(AuthResource):
    """
    Read API for follow lists, i.e, more than 1 follows
    """
    model_class = CFollow

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['company', 'follower']
        super(CFollowListAPI, self).__init__(*args, **kwargs)

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
        account_name = ""
        account_type = None
        sector_id = None
        industry_id = None
        following_follower = None
        if extra_query:
            if 'following_follower' in extra_query and extra_query[
                    'following_follower']:
                if extra_query['following_follower'] == CFOLLOW.CF_FOLLOWING:
                    query_filters['base'].append(
                        CFollow.sent_by == g.current_user['row_id'])
                    following_follower = CFOLLOW.CF_FOLLOWING
                elif extra_query['following_follower'] == CFOLLOW.CF_FOLLOWER:
                    following_follower = CFOLLOW.CF_FOLLOWER
                    query_filters['base'].append(
                        CFollow.company_id == g.current_user['account_id'])
            if "account_name" in extra_query and extra_query[
                    'account_name']:
                account_name = '%' + (
                    extra_query["account_name"]).lower() + '%'
            if "account_type" in extra_query and extra_query[
                    'account_type']:
                account_type = extra_query['account_type']
            if 'sector_id' in extra_query and extra_query['sector_id']:
                sector_id = extra_query['sector_id']
            if 'industry_id' in extra_query and extra_query['industry_id']:
                industry_id = extra_query['industry_id']
        else:
            # append base query filter to fetch following companies
            # of current user or followers of current account,
            # depending on query
            query_filters['base'].append(
                CFollow.sent_by == g.current_user['row_id'])

        if account_name == "":
            account_name = '%%'

        if sort:
            mapper = inspect(Account)
            sort_fxn = 'asc'
            if sort['sort'] == 'dsc':
                sort_fxn = 'desc'
            for sby in sort['sort_by']:
                if sby in mapper.columns:
                    order.append(getattr(mapper.columns[sby], sort_fxn)())
        query = self._build_final_query(query_filters, query_session, operator)
        # eager load account and user details
        # #TODO: improve by loading only required fields of user profile,
        # right now, if we load only required fields, it is making many queries
        query = query.options(
            # follower and related stuff
            joinedload(CFollow.follower).load_only(
                'row_id', 'account_id').joinedload(
                User.account).load_only(*account_fields),
            joinedload(CFollow.follower).load_only('row_id').joinedload(
                User.profile).joinedload(UserProfile.designation_link)).\
            join(Account, CFollow.company_id == Account.row_id).\
            join(User, CFollow.sent_by == User.row_id).\
            filter(
            func.lower(Account.account_name).like(account_name),
            Account.blocked==False)
        # if following so filter will be according to company related
        # if follower so filter will be according to user account related
        if following_follower == CFOLLOW.CF_FOLLOWING:
            query = query.join(
                AccountProfile,
                Account.row_id == AccountProfile.account_id)
        elif following_follower == CFOLLOW.CF_FOLLOWER:
            query = query.join(
                AccountProfile,
                User.account_id == AccountProfile.account_id)

        if account_type:
            query = query.filter(
                AccountProfile.account_type == account_type)
        if sector_id:
            query = query.filter(
                AccountProfile.sector_id == sector_id)
        if industry_id:
            query = query.filter(
                AccountProfile.industry_id == industry_id)

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/follow_get_list.yml')
    def get(self):
        """
        Get the list
        """
        follow_read_schema = CFollowReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            follow_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(CFollow), operator)
            # making a copy of the main output schema
            follow_schema = CFollowSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                follow_schema = CFollowSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching CFollow found')
            result = follow_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data, 'total': total}, 200


class CFollowAnalysisAPI(AuthResource):
    """
    Read follow list for Following analysis
    """

    @swag_from('swagger_docs/follow_analysis_get.yml')
    def get(self):
        """
        Get the list
        :return:
        """
        follow_analysis_schema = CFollowAnalysisSchema()
        try:
            total = 0
            cfollow_data = db.session.query(func.count(
                Designation.designation_level).label(
                'total_follow_by_designation'),
                Designation.designation_level).join(
                UserProfile, UserProfile.designation == Designation.name).join(
                User).join(CFollow).filter(
                CFollow.company_id == g.current_user['account_id']).group_by(
                Designation.designation_level).all()

            if not cfollow_data:
                c_abort(404, message='No matching CFollow found')
            total = sum([total + t.total_follow_by_designation
                         for t in cfollow_data])
            result = follow_analysis_schema.dump(cfollow_data, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data, 'total': total}, 200
