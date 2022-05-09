"""
API endpoints for "BSE CORP Feed" package.
"""

from datetime import datetime, time, timedelta, timezone
from werkzeug.exceptions import HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.orm import load_only, contains_eager, Load
from sqlalchemy import cast, and_, or_, func, any_, case
from app import db, c_abort
from app.base.api import AuthResource, BaseResource
from app.base.schemas import BaseReadArgsSchema
from app.common.utils import time_converter
from app.resources.bse.models import BSEFeed
from app.resources.bse.schemas import BseCorpSchema, BseFeedReadArgsSchema, BseFeedStatsSchema, BseFeedStatsReadArgsSchema
from app.resources.corporate_announcements_category.models import CorporateAnnouncementCategory
from app.resources.follows.models import CFollow
from app.resources.accounts.models import Account


class BSEFeedAPI(AuthResource):
    """
    Get a news source by id
    """
    def get(self, row_id):

        bse_corp_schema = BseCorpSchema()
        model = None
        try:
            # first find model
            model = BSEFeed.query.get(row_id)
            if model is None:
                c_abort(404, message='BSEFeed id: %s does not exist' %
                                     str(row_id))
            result = bse_corp_schema.dump(model)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class BSEFeedListAPI(AuthResource):
    """
        Read API for feed lists, i.e, more than 1 BSE Feed
    """
    model_class = BSEFeed

    def __init__(self, *args, **kwargs):
        super(BSEFeedListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        company_name = filters.pop('company_name', None)
        news_sub = filters.pop('news_sub', None)
        category_id = filters.pop('category_id', None)
        # build the default queries, using the parent helper
        query_filters, extra_query, db_projection, s_projection, order, \
        paging = self._build_query(
            filters, pfields, sort, pagination, operator,
            include_deleted=include_deleted)

        # build specific extra queries
        following = False
        if extra_query:
            if "from_date" in extra_query and extra_query['from_date']:
                started_at = extra_query.pop('from_date')
                started_at = time_converter(started_at, 'UTC', 'Asia/Kolkata')
                started_at = started_at.strftime("%Y-%m-%dT%H:%M:%SZ")
                query_filters['filters'].append(BSEFeed.dt_tm >= started_at)
            if "to_date" in extra_query and extra_query['to_date']:
                ended_to = extra_query.pop('to_date')
                ended_to = time_converter(ended_to, 'UTC', 'Asia/Kolkata')
                ended_to = ended_to.strftime("%Y-%m-%dT%H:%M:%SZ")
                query_filters['filters'].append(BSEFeed.dt_tm <= ended_to)
            if "following" in extra_query and extra_query['following']:
                following = extra_query['following']

        query = self._build_final_query(query_filters, query_session, operator)

        query = query.join(Account, BSEFeed.acc_id == Account.row_id)
        if news_sub and company_name:
            query = query.filter(or_(func.lower(BSEFeed.company_name).like('%' + company_name.lower() + '%'),
                                     func.lower(BSEFeed.news_sub).like('%' + news_sub.lower() + '%'),
                                     func.lower(Account.account_name).like('%' + company_name.lower() + '%')))
        if following:
            query = query.join(
                CFollow, CFollow.company_id == BSEFeed.acc_id
            ).filter(CFollow.sent_by == g.current_user['row_id'])

        if category_id:
            query = query.filter(BSEFeed.ec_category == int(category_id))

        return query, db_projection, s_projection, order, paging

    def get(self):
        """
        Get the list
        """
        bse_feed_read_schema = BseFeedReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            bse_feed_read_schema)


        try:
            # build the sql query
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(BSEFeed), operator)
            # making a copy of the main output schema
            bse_corp_schema = BseCorpSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                bse_corp_schema = BseCorpSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching news sources found')
            result = bse_corp_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200

class BSEFeedStatsAPI(AuthResource):

    def __init__(self, *args, **kwargs):
        super(BSEFeedStatsAPI, self).__init__(
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

        # Today and last day date and time with UTC timezone converter
        utc_now = datetime.now(timezone.utc)

        today_start = utc_now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(hours=23, minutes=59, seconds=59)
        yesterday_start = today_start - timedelta(days=1)
        yesterday_end = yesterday_start + timedelta(hours=23, minutes=59, seconds=59)

        # build specific extra queries
        query_today = db.session.query(CorporateAnnouncementCategory.name,
                        func.count(BSEFeed.ec_category)).join(BSEFeed,
                        CorporateAnnouncementCategory.row_id == BSEFeed.ec_category) \
                        .filter(and_(BSEFeed.dt_tm >= today_start, BSEFeed.dt_tm <= today_end)) \
                        .group_by(BSEFeed.ec_category, CorporateAnnouncementCategory.name)
        query_today = self._build_final_query(
            query_filters, query_today, operator, main_class=BSEFeed)
        query_yesterday = db.session.query(CorporateAnnouncementCategory.name,
                        func.count(BSEFeed.ec_category)).join(BSEFeed,
                        CorporateAnnouncementCategory.row_id == BSEFeed.ec_category)\
                        .filter(and_(BSEFeed.dt_tm >= yesterday_start, BSEFeed.dt_tm <= yesterday_end))\
                        .group_by(BSEFeed.ec_category, CorporateAnnouncementCategory.name)
        query_yesterday = self._build_final_query(
            query_filters, query_yesterday, operator, main_class=BSEFeed)
        return query_today, query_yesterday, today_start, yesterday_start

    def get(self):
        """
        Get bse feed stats
        """

        # making a copy of the main output schema
        bse_feed_stats_schema = BseFeedStatsSchema()
        bse_feed_read_stats_schema = BseFeedStatsReadArgsSchema()

        filters, pfields, sort, pagination, operator = self.parse_args(
            bse_feed_read_stats_schema)

        try:
            # build the sql query
            query_today, query_yesterday, today_date, yesterday_date = self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(BSEFeed), operator)
            # run the count query
            count_model = query_today
            if not query_today and not query_yesterday:
                c_abort(404, message='No matching stats found')
            # dump the results
            result = bse_feed_stats_schema.dump(count_model)

            # Initialize dictionaries
            yesterday = {}
            today = {}
            final_dict = {}
            # combine the group by day result
            for category, count in query_today.all():
                today[category] = count
            for category, count in query_yesterday.all():
                yesterday[category] = count
            for key, val in yesterday.items():
                if key not in today.keys():
                    final_dict[key] = {'yesterday': val, 'today': 0}
                else:
                    final_dict[key] = {'yesterday': val}
            for key, val in today.items():
                if key in final_dict:
                    z = final_dict[key].copy()
                    final_dict[key] = {**z, 'today': val}
                else:
                    final_dict[key] = {'yesterday': 0, 'today': val}

            result.data['categories'] = final_dict
            result.data['date'] = {'today': str(today_date.date()), 'yesterday': str(yesterday_date.date())}

        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data}, 200

