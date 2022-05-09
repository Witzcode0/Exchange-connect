"""
API endpoints for "twitter feed" package.
"""

from werkzeug.exceptions import HTTPException
from flask import current_app, request
from flask_restful import abort
from sqlalchemy.orm import load_only
from flasgger import swag_from
from sqlalchemy.exc import IntegrityError

from app import db, c_abort
from app.base import constants as APP
from app.base.api import BaseResource, AuthResource
from app.auth.decorators import role_permission_required
from app.resources.roles import constants as ROLE
from app.resources.twitter_feeds.models import TwitterFeeds, tweetaccounts
from app.resources.twitter_feeds.schemas import (
    TwitterFeedSchema, TwitterFeedReadArgsSchema, TwitterSourceFeedSchema)
from app.resources.accounts.models import Account
from queueapp.twitter_feeds.fetch_tweets import fetch_tweets
from app.domain_resources.domains.helpers import (
    get_domain_name, get_domain_info)


class TwitterSourceFeedAPI(AuthResource):
    """
    Create, update, delete API for "twitter feed source"
    """

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[ROLE.ERT_SU])
    def post(self):
        """
        Create a tweet source
        """
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)
        try:
            # validate and deserialize input into object
            data, errors = TwitterSourceFeedSchema().load(
                json_data)
            if errors:
                c_abort(422, errors=errors)
            # validate twitter user
            if not data.verify_user():
                c_abort(422, message='Could not verify twitter user.')

            data.follow_source()
            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
            fetch_tweets.s(True, data.row_id).delay()
        except HTTPException as e:
            raise e
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (news_url)=(http://www.scmp.com/rss/17/feed)
                # already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'TwitterFeedSource Added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201


class TwitterFeedListAPI(BaseResource):
    """
    Read API for "news item" lists, i.e, more than 1 "News item"
    """
    model_class = TwitterFeeds

    def __init__(self, *args, **kwargs):
        super(TwitterFeedListAPI, self).__init__(*args, **kwargs)

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

        # build specific extra queries
        if extra_query:
            pass
        query = self._build_final_query(query_filters, query_session, operator)
        if filters.get('account_id'):
            query = query.join(
                tweetaccounts,
                TwitterFeeds.row_id == tweetaccounts.c.tweet_id).join(
                Account, Account.row_id == tweetaccounts.c.account_id
            ).filter(Account.row_id == filters['account_id'])
        query = query.filter(
            TwitterFeeds.domain_id == get_domain_info(get_domain_name())[0])
        return query, db_projection, s_projection, order, paging

    def get(self):
        """
        Get the list
        """
        twitter_feed_read_schema = TwitterFeedReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            twitter_feed_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(TwitterFeeds), operator)
            # making a copy of the main output schema
            twitter_feed_schema = TwitterFeedSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                twitter_feed_schema = TwitterFeedSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching twitters found')
            result = twitter_feed_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
