"""
API endpoints for "user profile" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import current_app
from flask_restful import abort

from app import db, c_abort
from app.base.api import AuthResource
from app.resources.user_profiles.models import UserProfile
from app.resources.user_profiles.schemas import (
    UserProfileChatSchema, UserProfileChatReadArgsSchema)


# schema for user profile chat
user_profile_chat_schema = UserProfileChatSchema()
# schema for reading get arguments
user_profile_chat_read_schema = UserProfileChatReadArgsSchema(strict=True)


class UserProfileChatAPI(AuthResource):
    """
    Get API for user profile chat
    """

    def get(self):
        """
        Get users by ids
        """
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            user_profile_chat_read_schema)
        models = []
        try:
            # first find model
            models = db.session.query(UserProfile).filter(
                UserProfile.user_id.in_(filters['user_ids'])).all()

            if not models:
                c_abort(404, message='User Profile id: %s does not exist' %
                        str(filters['user_ids']))

            result = user_profile_chat_schema.dump(models, many=True)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data}, 200
