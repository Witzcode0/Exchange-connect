"""
API endpoints for "news item archive" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.resources.news.models import NewsItem
from app.resources.news_archive.models import NewsItemArchive
from app.resources.news_archive.schemas import (
    NewsItemArchiveSchema, NewsItemArchiveReadArgsSchema)
from app.base import constants as APP


class NewsItemArchiveAPI(AuthResource):
    """
    Create, update, delete API for "news item archive"
    """

    @swag_from('swagger_docs/news_archive_post.yml')
    def post(self, news_item_id):
        """
        Create a news item archive
        """
        news_item_archive_schema = NewsItemArchiveSchema()
        model = None
        json_data = {}
        try:
            # first find model
            model = NewsItem.query.get(news_item_id)
            if model is None:
                c_abort(404, message='NewsItem id: %s does not exist' %
                                     str(news_item_id))
            json_data['guid'] = model.guid
            json_data['title'] = model.title
            json_data['link'] = model.link
            json_data['posted_at'] = str(model.posted_at)
            json_data['description'] = model.description
            json_data['tags'] = model.tags
            json_data['news_name'] = model.news_name
            json_data['news_url'] = model.news_url
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        try:
            # validate and deserialize input
            data, errors = news_item_archive_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            data.news_id = model.row_id
            data.created_by = g.current_user['row_id']
            data.account_id = g.current_user['account_id']
            data.updated_by = data.created_by
            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
        except HTTPException as e:
            raise e
        except Forbidden as e:
            raise e
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (news_id, created_by)=(1, 1) already exists.
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

        return {'message': 'NewsItem archive Added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @swag_from('swagger_docs/news_archive_delete.yml')
    def delete(self, row_id):
        """
        Delete a news item archive
        """
        model = None
        try:
            # first find model
            model = NewsItemArchive.query.get(row_id)
            if model is None:
                c_abort(404, message='NewsItem id: %s does not exist' %
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

    @swag_from('swagger_docs/news_archive_get.yml')
    def get(self, row_id):
        """
        Get a news item archive by id
        """
        news_item_archive_schema = NewsItemArchiveSchema()
        model = None
        try:
            # first find model
            model = NewsItemArchive.query.get(row_id)
            if model is None:
                c_abort(404, message='NewsItem archive id: %s does not exist' %
                                     str(row_id))
            result = news_item_archive_schema.dump(model)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class NewsItemArchiveListAPI(AuthResource):
    """
    Read API for "news item archive" lists, i.e, more than 1 "news item"
    """
    model_class = NewsItemArchive

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['account', 'creator', 'news', ]
        super(NewsItemArchiveListAPI, self).__init__(*args, **kwargs)

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
        query_filters['base'].append(
            NewsItemArchive.created_by == g.current_user['row_id'])
        query = self._build_final_query(query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/news_archive_get_list.yml')
    def get(self):
        """
        Get the list
        """
        news_item_archive_read_schema = NewsItemArchiveReadArgsSchema(
            strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            news_item_archive_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(NewsItemArchive), operator)
            # making a copy of the main output schema
            news_item_archive_schema = NewsItemArchiveSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                news_item_archive_schema = NewsItemArchiveSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(
                    404, message='No matching news items archive found')
            result = news_item_archive_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
