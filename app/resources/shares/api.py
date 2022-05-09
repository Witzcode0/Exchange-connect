"""
API endpoints for "shares" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_
from sqlalchemy.orm import load_only, joinedload
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.resources.posts.models import Post
from app.resources.posts.schemas import PostSchema

from queueapp.feed_tasks import add_post_feed
from app.base import constants as APP


class ShareAPI(AuthResource):
    """
    Create API for post share
    """

    @swag_from('swagger_docs/share_post.yml')
    def post(self):
        """
        Create post
        """

        post_schema = PostSchema()
        model = []
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = post_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # check shared post already shared or not
            model = Post.query.filter(and_(
                Post.row_id == data.post_shared_id, Post.shared)).options(
                load_only('post_shared_id', 'shared')).first()

            if model:
                data.post_shared_id = model.post_shared_id

            data.created_by = g.current_user['row_id']
            data.account_id = g.current_user['account_id']
            data.updated_by = data.created_by
            data.shared = True

            db.session.add(data)
            db.session.commit()

            # add in feed
            add_post_feed.s(True, data.row_id).delay()
        except HTTPException as e:
            raise e
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (post_shared_id)=(6) is not present in table "post".
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message='Post does not exist', errors={
                    column: ['Post does not exist']})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Post share added %s' % str(data.row_id),
                'row_id': data.row_id}, 201
