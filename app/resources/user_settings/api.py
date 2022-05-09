"""
API endpoints for "user settings" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.orm import joinedload
from flasgger.utils import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.resources.user_settings.models import UserSettings
from app.resources.user_settings.schemas import UserSettingsSchema


class UserSettingsAPI(AuthResource):
    """
    Put and Get API for user settings
    """

    @swag_from('swagger_docs/user_settings_put.yml')
    def put(self):
        """
        Update user settings
        """
        user_settings_schema = UserSettingsSchema()
        # first find model
        model = None
        try:
            model = UserSettings.query.options(joinedload(
                UserSettings.user)).filter_by(
                user_id=g.current_user['row_id']).first()
            if model is None or model.deleted:
                c_abort(404, message='User Settings id: %s does not exist' %
                                     str(g.current_user['row_id']))
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
            data, errors = user_settings_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
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
        return {'message': 'Updated User Settings id: %s' %
                           str(model.user_id)}, 200

    @swag_from('swagger_docs/user_settings_get.yml')
    def get(self):
        """
        Get user settings
        """

        user_settings_schema = UserSettingsSchema()
        model = None
        try:
            # first find model
            model = UserSettings.query.options(joinedload(
                UserSettings.user)).filter_by(
                user_id=g.current_user['row_id']).first()
            if model is None or model.deleted:
                c_abort(404, message='User Settings id: %s does not exist' %
                                     str(g.current_user['row_id']))
            result = user_settings_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200
