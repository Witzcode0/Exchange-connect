"""
API endpoints for "news wire post" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only, joinedload
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.base import constants as APP
from app.newswire_resources.newswire_posts.models import NewswirePost
from app.newswire_resources.newswire_posts.schemas import (
    NewswirePostSchema, NewswirePostReadArgsSchema)
from app.newswire_resources.newswire_post_file_library.models import \
    NewswirePostLibraryFile


class NewswirePostAPI(AuthResource):
    """
    Create, update, delete API for news wire post
    """
    @swag_from('swagger_docs/news_wire_post_post.yml')
    def post(self):
        """
        Create news wire post
        """
        news_wire_post_schema = NewswirePostSchema()
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = news_wire_post_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            data.created_by = g.current_user['row_id']
            data.account_id = g.current_user['account_id']
            data.updated_by = data.created_by

            db.session.add(data)
            db.session.commit()
            # manage files list
            if news_wire_post_schema._cached_files:
                for cf in news_wire_post_schema._cached_files:
                    if cf not in data.files:
                        data.files.append(cf)
            db.session.add(data)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (logo_file_id)=(1000) is not present in table
                # "newswire_post_library_file"
                column = e.orig.diag.message_detail.split('(')[1].split(')')[0]
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

        return {'message': 'Newswire Post added %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @swag_from('swagger_docs/news_wire_post_put.yml')
    def put(self, row_id):
        """
        Update news wire post by id
        """
        news_wire_post_schema = NewswirePostSchema()
        model = None
        try:
            model = NewswirePost.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Newswire Post id: %s does not exist' %
                                     str(row_id))
            # only current user can change news wire post
            if model.created_by != g.current_user['row_id']:
                c_abort(401)
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            data, errors = news_wire_post_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            if news_wire_post_schema._cached_files or 'file_ids' in json_data:
                # add new ones
                for cf in news_wire_post_schema._cached_files:
                    if cf not in data.files:
                        data.files.append(cf)
                # remove old ones
                for oldcf in data.files[:]:
                    if oldcf not in news_wire_post_schema._cached_files:
                        data.files.remove(oldcf)
            db.session.add(data)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (logo_file_id)=(1000) is not present in table
                # "newswire_post_library_file"
                column = e.orig.diag.message_detail.split('(')[1].split(')')[0]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except HTTPException as e:
            raise e
        except Forbidden as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Updated Newswire Post id: %s' % str(row_id)}, 200

    @swag_from('swagger_docs/news_wire_post_delete.yml')
    def delete(self, row_id):
        """
        Delete news wire post by id
        """
        model = None
        try:
            model = NewswirePost.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Newswire Post id: %s does not exist' %
                                     str(row_id))
            if model.created_by != g.current_user['row_id']:
                c_abort(401)

            model.deleted = True
            db.session.add(model)
            db.session.commit()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {}, 204

    @swag_from('swagger_docs/news_wire_post_get.yml')
    def get(self, row_id):
        """
        Get news wire post by id
        """
        news_wire_post_schema = NewswirePostSchema()
        model = None
        try:
            # first find model
            model = NewswirePost.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Newswire Post id: %s does not exist' %
                                     str(row_id))
            result = news_wire_post_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result}, 200


class NewswirePostListAPI(AuthResource):
    """
    Read API for news wire post lists, i.e, more than news wire post
    """

    model_class = NewswirePost

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['creator', 'account', 'editor', 'files']
        super(NewswirePostListAPI, self).__init__(*args, **kwargs)

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
            for f in extra_query:
                # files
                if f == 'file_ids':
                    query_filters['filters'].append(
                        NewswirePostLibraryFile.row_id.in_(filters[f]))
                    innerjoin = True
                    continue

        query_filters['base'].append(
            NewswirePost.created_by == g.current_user['row_id'])
        query = self._build_final_query(query_filters, query_session, operator)

        if innerjoin:
            query = query.join(NewswirePost.files)
        else:
            query = query.options(joinedload(NewswirePost.files))

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/news_wire_post_get_list.yml')
    def get(self):
        """
        Get the list
        """
        news_wire_post_read_schema = NewswirePostReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            news_wire_post_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(NewswirePost), operator)
            # making a copy of the main output schema
            news_wire_post_schema = NewswirePostSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                news_wire_post_schema = NewswirePostSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching news wire posts found')
            result = news_wire_post_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data, 'total': total}, 200
