"""
API endpoints for "feeds" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import current_app, g
from flask_restful import abort
from sqlalchemy.orm import load_only, joinedload, contains_eager
from sqlalchemy import and_
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.resources.feeds.models import FeedItem
from app.resources.feeds.schemas import (
    FeedItemSchema, FeedItemReadArgsSchema)
from app.resources.post_stars.models import PostStar
from app.resources.post_comments.models import PostComment


class FeedItemAPI(AuthResource):
    """
    Get API for feed
    """

    @swag_from('swagger_docs/feed_item_get.yml')
    def get(self, row_id):
        """
        Get feed by id
        """
        feed_item_schema = FeedItemSchema()
        model = None
        try:
            model = FeedItem.query.get(row_id)
            if model is None:
                c_abort(404, message='FeedItem id: %s does not exist' %
                                     str(row_id))
            result = feed_item_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result}, 200


class FeedItemListAPI(AuthResource):
    """
    Read API for feed lists, i.e, more than
    """

    model_class = FeedItem

    def __init__(self, *args, **kwargs):
        super(FeedItemListAPI, self).__init__(*args, **kwargs)

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
        # join outer
        innerjoin = False

        # build specific extra queries filters
        if extra_query:
            pass

        # user filter
        query_filters['base'].append(
            FeedItem.user_id == g.current_user['row_id'])
        query = self._build_final_query(query_filters, query_session, operator)

        query = query.join(
            PostStar, and_(
                PostStar.post_id == FeedItem.post_id,
                PostStar.created_by == g.current_user['row_id']),
            isouter=True).join(
            PostComment, and_(
                PostComment.post_id == FeedItem.post_id,
                PostComment.created_by == g.current_user['row_id']),
            isouter=True).options(
            # let it know that this is already loaded
            contains_eager(FeedItem.feed_starred),
            contains_eager(FeedItem.feed_commented),
            joinedload(FeedItem.post))

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/feed_item_get_list.yml')
    def get(self):
        """
        Get the list
        """
        feed_item_read_schema = FeedItemReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            feed_item_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(FeedItem), operator)
            # making a copy of the main output schema
            feed_item_schema = FeedItemSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                feed_item_schema = FeedItemSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching feed found')
            result = feed_item_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data, 'total': total}, 200
