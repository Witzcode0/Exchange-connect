"""
API endpoints for "posts" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
# from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only, joinedload, contains_eager, Load
from sqlalchemy import and_
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.resources.posts.models import Post
from app.resources.posts.schemas import PostSchema, PostReadArgsSchema
from app.resources.post_file_library.models import PostLibraryFile
from app.resources.post_stars.models import PostStar
from app.resources.post_comments.models import PostComment
from app.resources.feeds.models import FeedItem

from queueapp.feed_tasks import add_post_feed


class PostAPI(AuthResource):
    """
    Create, update, delete API for post
    """
    @swag_from('swagger_docs/post_post.yml')
    def post(self):
        """
        Create post
        """
        post_schema = PostSchema()
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = post_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            data.created_by = g.current_user['row_id']
            data.account_id = g.current_user['account_id']
            data.updated_by = data.created_by

            db.session.add(data)
            db.session.commit()
            # manage files list
            if post_schema._cached_files:
                for cf in post_schema._cached_files:
                    if cf not in data.files:
                        data.files.append(cf)
            db.session.add(data)
            db.session.commit()
            # add in feed
            add_post_feed.s(True, data.row_id).delay()
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Post added %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @swag_from('swagger_docs/post_put.yml')
    def put(self, row_id):
        """
        Update post by id
        """
        post_schema = PostSchema()
        model = None
        try:
            model = Post.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Post id: %s does not exist' %
                                     str(row_id))
            # only current user can change post
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
            data, errors = post_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.edited = True
            data.updated_by = g.current_user['row_id']
            if post_schema._cached_files or 'file_ids' in json_data:
                # add new ones
                for cf in post_schema._cached_files:
                    if cf not in data.files:
                        data.files.append(cf)
                # remove old ones
                for oldcf in data.files[:]:
                    if oldcf not in post_schema._cached_files:
                        data.files.remove(oldcf)
            db.session.add(data)
            db.session.commit()
        except HTTPException as e:
            raise e
        except Forbidden as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Updated Post id: %s' % str(row_id)}, 200

    @swag_from('swagger_docs/post_delete.yml')
    def delete(self, row_id):
        """
        Delete post by id
        """
        model = None
        try:
            model = Post.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Post id: %s does not exist' %
                                     str(row_id))
            if model.created_by != g.current_user['row_id']:
                c_abort(401)

            model.deleted = True
            db.session.add(model)
            db.session.commit()
            # when post delete then all feeds delete which are hold
            # particular post_id
            FeedItem.query.filter(FeedItem.post_id == row_id).delete()
            db.session.commit()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {}, 204

    @swag_from('swagger_docs/post_get.yml')
    def get(self, row_id):
        """
        Get post by id
        """
        model = None
        try:
            # first find model
            model = Post.query.filter_by(row_id=row_id).join(
                PostStar, and_(
                    PostStar.post_id == Post.row_id,
                    PostStar.created_by == g.current_user['row_id']),
                isouter=True).join(
                PostComment, and_(
                    PostComment.post_id == Post.row_id,
                    PostComment.created_by == g.current_user['row_id']),
                isouter=True).options(
                # let it know that this is already loaded
                contains_eager(Post.post_starred),
                contains_eager(Post.post_commented),
                # load only certain columns from joined table
                # #TODO: make this work later
                Load(PostStar).load_only('row_id', 'post_id', 'created_by'),
                Load(PostComment).load_only('row_id', 'post_id', 'created_by'),
                # load the account name
                joinedload(Post.creator).load_only('account_id')).first()
            if model is None or model.deleted:
                c_abort(404, message='Post id: %s does not exist' %
                                     str(row_id))
            result = PostSchema(
                exclude=PostSchema._default_exclude_fields).dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result}, 200


class PostListAPI(AuthResource):
    """
    Read API for post lists, i.e, more than 1 post
    """

    model_class = Post

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['post_starred', 'post_commented']
        super(PostListAPI, self).__init__(*args, **kwargs)

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
                        PostLibraryFile.row_id.in_(filters[f]))
                    innerjoin = True
                    continue

        # #TODO: user filter used in future
        # query_filters['base'].append(
        #     Post.created_by == g.current_user['row_id'])
        query = self._build_final_query(query_filters, query_session, operator)
        # eager load the post star and comment status
        query = query.join(
            PostStar, and_(
                PostStar.post_id == Post.row_id,
                PostStar.created_by == g.current_user['row_id']),
            isouter=True).join(
            PostComment, and_(
                PostComment.post_id == Post.row_id,
                PostComment.created_by == g.current_user['row_id']),
            isouter=True).options(
                # let it know that this is already loaded
                contains_eager(Post.post_starred),
                contains_eager(Post.post_commented),
                # load only certain columns from joined table
                # #TODO: make this work later
                Load(PostStar).load_only('row_id', 'post_id', 'created_by'),
                Load(PostComment).load_only('row_id', 'post_id', 'created_by'),
                # load the account name
                joinedload(Post.creator).load_only('account_id'))

        if innerjoin:
            query = query.join(Post.files)
        else:
            query = query.options(joinedload(Post.files))
        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/post_get_list.yml')
    def get(self):
        """
        Get the list
        """
        post_read_schema = PostReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            post_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Post), operator)
            # making a copy of the main output schema
            post_schema = PostSchema(
                exclude=PostSchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                post_schema = PostSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching posts found')
            result = post_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data, 'total': total}, 200
