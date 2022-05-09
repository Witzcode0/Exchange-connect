"""
API endpoints for "admin post comments" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import current_app
from flask_restful import abort
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.auth.decorators import role_permission_required
from app.resources.roles import constants as ROLE
from app.resources.post_comments.models import PostComment


class AdminPostCommentAPI(AuthResource):
    """
    delete post comment by admin
    """
    @role_permission_required(perms=[ROLE.EPT_NU])
    @swag_from('swagger_docs/admin_post_comment_delete.yml')
    def delete(self, row_id):
        """
        Delete post comment by id
        """
        model = None
        try:
            # first find model
            model = PostComment.query.get(row_id)
            if model is None:
                c_abort(404, message='Post Comment id: %s does not exist' %
                                     str(row_id))
            # if model is found, and not yet deleted, delete it.
            db.session.delete(model)
            db.session.commit()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {}, 204
