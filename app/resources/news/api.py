"""
API endpoints for "news" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only, contains_eager, Load
from flasgger import swag_from
from sqlalchemy import Date, cast, func

from app import db, c_abort
from app.base.api import AuthResource, BaseResource
from app.base.schemas import BaseReadArgsSchema
from app.resources.news.models import (NewsSource, NewsItem, newsaccounts,
    TopNews)
from app.resources.news.schemas import (
    NewsSourceSchema, NewsItemSchema, NewsItemReadArgsSchema, TopNewsSchema,
    TopNewsReadArgSchema)
from app.resources.news_archive.models import NewsItemArchive
from app.base import constants as APP
from app.resources.accounts.models import Account
from app.resources.follows.models import CFollow
from app.domain_resources.domains.helpers import (
    get_domain_name, get_domain_info)


class NewsSourceAPI(AuthResource):
    """
    Create, update, delete API for "news source"
    """

    def _validate_source(self):
        """
        Validate the news source
        """
        pass

    @swag_from('swagger_docs/news_source_post.yml')
    def post(self):
        """
        Create a news source
        """
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)
        try:
            # validate and deserialize input into object
            data, errors = NewsSourceSchema(exclude=['news_name']).load(
                json_data)
            if errors:
                c_abort(422, errors=errors)
            # validate news source
            if not NewsSource.verify_source(data):
                c_abort(422, message='Could not verify source')

            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
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

        return {'message': 'NewsSource Added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @swag_from('swagger_docs/news_source_put.yml')
    def put(self, row_id):
        """
        Update a news source, either pass file data as multipart-form,
        or json data
        """
        news_source_schema = NewsSourceSchema()
        # first find model
        model = None
        try:
            model = NewsSource.query.get(row_id)
            if model is None:
                c_abort(404, message='NewsSource id: %s does not exist' %
                        str(row_id))
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input
            data, errors = news_source_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # validate news source
            if not NewsSource.verify_source(data, update_name=False):
                c_abort(422, message='Could not verify source')
            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
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
        return {'message': 'Updated news Source id: %s' % str(row_id)}, 200

    @swag_from('swagger_docs/news_source_delete.yml')
    def delete(self, row_id):
        """
        Delete a news source
        """
        model = None
        try:
            # first find model
            model = NewsSource.query.get(row_id)
            if model is None:
                c_abort(404, message='NewsSource id: %s does not exist' %
                                     str(row_id))
            db.session.delete(model)
            db.session.commit()
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204

    @swag_from('swagger_docs/news_source_get.yml')
    def get(self, row_id):
        """
        Get a news source by id
        """
        news_source_schema = NewsSourceSchema()
        model = None
        try:
            # first find model
            model = NewsSource.query.get(row_id)
            if model is None:
                c_abort(404, message='NewsSource id: %s does not exist' %
                                     str(row_id))
            result = news_source_schema.dump(model)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class NewsSourceListAPI(AuthResource):
    """
    Read API for "news source" lists, i.e, more than 1 "news source"
    """
    model_class = NewsSource

    def __init__(self, *args, **kwargs):
        super(NewsSourceListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        # build the default queries, using the parent helper
        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)

        # build specific extra queries
        if extra_query:
            pass

        query = self._build_final_query(query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/news_source_get_list.yml')
    def get(self):
        """
        Get the list
        """
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            BaseReadArgsSchema(strict=True))
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(NewsSource), operator)
            # making a copy of the main output schema
            news_source_schema = NewsSourceSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                news_source_schema = NewsSourceSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching news sources found')
            result = news_source_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class NewsItemListAPI(AuthResource):
    """
    Read API for "news item" lists, i.e, more than 1 "News item"
    """
    model_class = NewsItem

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['news_archived']
        super(NewsItemListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        # build the default queries, using the parent helper
        if 'title' in filters and filters['title']:
            filters['description'] = filters['title']

        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)

        # build specific extra queries
        account_id = None
        following = False
        if extra_query:
            if 'account_id' in extra_query and extra_query['account_id']:
                account_id = extra_query['account_id']
            if 'following' in extra_query and extra_query['following']:
                following = extra_query['following']

        query = self._build_final_query(query_filters, query_session, operator)
        # eager load the archive status
        query = query.join(
            NewsItemArchive, and_(
                NewsItemArchive.news_id == NewsItem.row_id,
                NewsItemArchive.created_by == g.current_user['row_id']),
            isouter=True).options(
                # let it know that this is already loaded
                contains_eager(NewsItem.news_archived),
                # load only certain columns from joined table
                # #TODO: make this work later
                Load(NewsItemArchive).load_only(
                    'row_id', 'news_id', 'created_by'))

        if account_id:
            query = query.join(
                newsaccounts, NewsItem.row_id == newsaccounts.c.news_id).join(
                Account, Account.row_id == newsaccounts.c.account_id).filter(
                Account.row_id == account_id)
        if following:
            query = query.join(
                newsaccounts, NewsItem.row_id == newsaccounts.c.news_id
            ).join(
                Account, Account.row_id == newsaccounts.c.account_id
            ).join(
                CFollow, CFollow.company_id == Account.row_id
            ).filter(CFollow.sent_by == g.current_user['row_id'])

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/news_get_list.yml')
    def get(self):
        """
        Get the list
        """
        news_item_read_schema = NewsItemReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            news_item_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(NewsItem), operator)
            # making a copy of the main output schema
            news_item_schema = NewsItemSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                news_item_schema = NewsItemSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching news items found')
            result = news_item_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class NewsItemNoAuthListAPI(BaseResource):
    """
    Read API for "news item" lists, i.e, more than 1 "News item"
    """
    model_class = NewsItem

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['news_archived']
        super(NewsItemNoAuthListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        # build the default queries, using the parent helper
        if 'title' in filters and filters['title']:
            filters['description'] = filters['title']

        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)

        # build specific extra queries
        account_id = None
        if extra_query:
            if 'account_id' in extra_query and extra_query['account_id']:
                account_id = extra_query['account_id']

        query = self._build_final_query(query_filters, query_session, operator)

        if account_id:
            query = query.join(
                newsaccounts, NewsItem.row_id == newsaccounts.c.news_id).join(
                Account, Account.row_id == newsaccounts.c.account_id).filter(
                Account.row_id == account_id)
        query = query.filter(
            NewsItem.domain_id == get_domain_info(get_domain_name())[0])

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/news_get_list.yml')
    def get(self):
        """
        Get the list
        """
        news_item_read_schema = NewsItemReadArgsSchema(strict=True)
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            news_item_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(NewsItem), operator)
            # making a copy of the main output schema
            news_item_schema = NewsItemSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                news_item_schema = NewsItemSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching news items found')
            result = news_item_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class TopNewsAPI(AuthResource):
    """
    Create, update, delete API for "Top news"
    """

    def post(self):
        """
        Create a top news
        """
        json_data = request.get_json()
        if not json_data:
            c_abort(400)
        try:
            # check for user already exist with particular date and domain_id
            user_data = TopNews.query.filter(and_(
                    TopNews.date == json_data['date'],
                    TopNews.domain_id == json_data['domain_id'])).first()
            if user_data:
                c_abort(422,
                    {'message':'TopNews: with {} already exist'.format(json_data['date'])})

            # validate and deserialize input into object
            data, errors = TopNewsSchema().load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()
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

        return {'message': 'Top News Added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    def put(self, row_id):
        """
        Update a top news json data,
        """
        top_news_schema = TopNewsSchema()
        # first find model
        model = None
        try:
            model = TopNews.query.get(row_id)
            if model is None:
                c_abort(404, message='TopNews id: %s does not exist' %
                        str(row_id))
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input
            data, errors = top_news_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # update user
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()
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
        return {'message': 'Updated Top news id: %s' % str(row_id)}, 200

    def delete(self, row_id):
        """
        Delete an top news by id
        """
        model = None
        try:
            # first find model
            model = TopNews.query.get(row_id)
            if model is None:
                c_abort(404, message='Top news id: %s does not exist' %
                                     str(row_id))
            db.session.delete(model)
            db.session.commit()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204

    def get(self, row_id):
        """
        Get an top news by id
        """
        top_news_schema = TopNewsSchema()
        model = None
        try:
            # first find model
            model = TopNews.query.get(row_id)
            if model is None:
                c_abort(404, message='Top news id: %s does not exist' %
                                     str(row_id))
            result = top_news_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class TopNewsListAPI(AuthResource):
    """
    Read API for "Top News" lists, i.e, more than 1 "News"
    """
    model_class = TopNews

    def __init__(self, *args, **kwargs):
        super(TopNewsListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        # build the default queries, using the parent helper

        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)

        # build specific extra queries
        if extra_query:
            if "from_date" in extra_query and extra_query['from_date']:
                started_at = extra_query.pop('from_date')
                query_filters['filters'].append(TopNews.date >= started_at)
            if "to_date" in extra_query and extra_query['to_date']:
                ended_to = extra_query.pop('to_date')
                query_filters['filters'].append(TopNews.date <= ended_to)

        query = self._build_final_query(query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    def get(self):
        """
        Get the list
        """
        top_news_read_schema = TopNewsReadArgSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            top_news_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(TopNews), operator)
            # making a copy of the main output schema
            news_item_schema = TopNewsSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                news_item_schema = TopNewsSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching news items found')
            result = news_item_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200