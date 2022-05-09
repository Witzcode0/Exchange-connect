"""
API endpoints for "admin posts" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import current_app
from flask_restful import abort
from sqlalchemy.orm import load_only, joinedload
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.auth.decorators import role_permission_required
from app.resources.posts.models import Post
from app.resources.posts.schemas import PostSchema, AdminPostReadArgsSchema
from app.resources.post_file_library.models import PostLibraryFile
from app.resources.roles import constants as ROLE
from app.resources.feeds.models import FeedItem


class AdminPostAPI(AuthResource):
    """
    get, delete posts by admin
    """
    @role_permission_required(perms=[ROLE.EPT_NU])
    @swag_from('swagger_docs/admin_post_delete.yml')
    def delete(self, row_id):
        """
        Delete post by id
        """
        model = None
        try:
            # first find model
            model = Post.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Post id: %s does not exist' %
                                     str(row_id))
            # if model is found, and not yet deleted, delete it.
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

    @role_permission_required(perms=[ROLE.EPT_NU])
    @swag_from('swagger_docs/admin_post_get.yml')
    def get(self, row_id):
        """
        Get post by id
        """
        model = None
        try:
            # first find model
            model = Post.query.get(row_id)
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


class AdminPostListAPI(AuthResource):
    """
    Read API for admin post lists, i.e, more than 1 post
    """

    model_class = Post

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['post_starred', 'post_commented']
        super(AdminPostListAPI, self).__init__(*args, **kwargs)

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

        query = self._build_final_query(query_filters, query_session, operator)
        query = query.options(joinedload(Post.shared_post))

        if innerjoin:
            query = query.join(Post.files)
        else:
            query = query.options(joinedload(Post.files))
        return query, db_projection, s_projection, order, paging

    @role_permission_required(perms=[ROLE.EPT_NU])
    @swag_from('swagger_docs/admin_post_get_list.yml')
    def get(self):
        """
        Get the list
        """
        admin_post_read_schema = AdminPostReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            admin_post_read_schema)
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
