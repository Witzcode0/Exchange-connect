"""
API endpoints for admin login as normal user.
"""

import datetime

from werkzeug.exceptions import HTTPException
from flask import request, current_app, g
from flask_restful import abort
from flask_jwt_extended import create_access_token, jwt_required
from marshmallow.exceptions import ValidationError
from flasgger.utils import swag_from
from sqlalchemy.orm import joinedload

from app import db, c_abort
from app.base.api import AuthResource, BaseResource, load_current_user
from app.resources.users.models import User
from app.auth.decorators import role_permission_required
from app.auth.schemas import LoginSchema, UserIdentitySchema
from app.resources.roles import constants as ROLE
from app.resources.accounts import constants as ACCOUNT


class AdminLoginAsAPI(AuthResource):
    """
    API to login admin as a normal user
    """
    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_MNG])
    @swag_from('swagger_docs/admin_login_post.yml')
    def post(self):
        """
        Login the user
        """
        login_schema = LoginSchema(strict=True)
        identity_schema = UserIdentitySchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            return c_abort(400)

        ret = {}
        try:
            # validate and deserialize input into object
            data, errors = login_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            super_admin = User.query.options(joinedload(
                User.profile)).filter_by(
                email=g.current_user['email']).first()

            if super_admin and super_admin.check_password(data['password']):
                user = User.query.options(joinedload(
                    User.profile)).filter_by(email=data['email']).first()

                if user and (user.deactivated is True or user.deleted is True):
                    c_abort(403, message='User is Deactivated, '
                            'Please Contact to Administrator')
                if user and user.unverified:
                    c_abort(403, message='Email not verified. Please verify '
                            'or contact administrator.')
                if user and user.settings.allow_admin_access is False:
                    c_abort(403, message='Not allowed, User has not given '
                            'permission')

                if user:
                    expires_delta = current_app.config[
                        'JWT_ACCESS_TOKEN_EXPIRES']
                    # assign current account as a account
                    user.current_account = user.account
                    result = identity_schema.dump(user)
                    ret = {'access_token': create_access_token(
                        identity=result.data, expires_delta=expires_delta)}
                    user.token_valid = True
                    db.session.add(user)
                    db.session.commit()
                else:
                    c_abort(401, message='Invalid Username or Password')
            else:
                c_abort(401, message='Invalid Username or Password')

        except ValidationError as e:
            c_abort(422, errors=e.messages)
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            abort(500)

        return ret, 200


class AdminLoginAPI(BaseResource):
    """
    API to login/logout users
    """

    def post(self):
        """
        Login the user
        """
        login_schema = LoginSchema(strict=True)
        identity_schema = UserIdentitySchema()
        login = None
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            return c_abort(400)

        ret = {}
        try:
            # validate and deserialize input into object
            data, errors = login_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            user = User.query.options(joinedload(
                User.profile)).filter_by(email=data['email']).first()

            if user:
                if user.account_type != ACCOUNT.ACCT_ADMIN:
                    c_abort(401, message='You are not authorized to login.')
            else:
                c_abort(401, message='Invalid Username or Password')

            if user and (user.deactivated is True or user.deleted is True):
                c_abort(403, message='User is Deactivated, '
                                     'Please Contact to Administrator')

            if user and user.unverified:
                c_abort(403, message='Email not verified. Please verify or '
                                     'contact administrator.')

            if user:
                if user.login_locked:
                    c_abort(401, message='Your account has been locked, '
                            'you\'ve exceeded the number of login attempts. '
                            'Please go to Forgot Password to reset again.')
                if not user.check_password(data['password']):
                    if not user.login_locked:
                        user.unsuccessful_login_count += 1
                        db.session.add(user)
                        db.session.commit()
                    c_abort(401, message='Invalid Username or Password')
                else:
                    expires_delta = current_app.config[
                        'JWT_ACCESS_TOKEN_EXPIRES']

                # assign current account as a account
                user.current_account = user.account
                result = identity_schema.dump(user)
                ret = {'access_token': create_access_token(
                    identity=result.data, expires_delta=expires_delta)}
                user.token_valid = True
                user.last_login = datetime.datetime.utcnow()
                user.unsuccessful_login_count = 0
                db.session.add(user)
                db.session.commit()
        except ValidationError as e:
            c_abort(422, errors=e.messages)
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            abort(500)

        return ret, 200

    @jwt_required
    @load_current_user
    def put(self):
        """
        Refresh token
        """
        identity_schema = UserIdentitySchema()
        ret = {}
        try:
            user = User.query.get(g.current_user['row_id'])
            if user and user.account_type != ACCOUNT.ACCT_ADMIN:
                c_abort(401, message='You are not authorized to login.')

            if user and (user.deactivated is True or user.deleted is True):
                c_abort(403, message='User is Deactivated, '
                                     'Please Contact to Administrator')

            if user and user.unverified:
                c_abort(403, message='Email not verified. Please verify or '
                                     'contact administrator.')

            if user:
                expires_delta = current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
                # assign current account as a account
                user.current_account = user.account
                result = identity_schema.dump(user)
                ret = {'access_token': create_access_token(
                    identity=result.data, expires_delta=expires_delta)}
            else:
                c_abort(404, message='User not found')

        except HTTPException as e:
            raise e
        except Exception as e:
            abort(500)

        return ret, 200

    @jwt_required
    @load_current_user
    def get(self):
        current_user = g.current_user
        # clean current_user
        # remove the account_model as it is internal object
        del current_user['account_model']

        return {'user': current_user}, 200

    @jwt_required
    @load_current_user
    def delete(self):
        """
        Logout user
        """
        ret = {}
        try:
            user = User.query.get(g.current_user['row_id'])

            if user and user.account_type == ACCOUNT.ACCT_ADMIN:
                user.token_valid = False
                user.last_logout = datetime.datetime.utcnow()
                db.session.add(user)
                db.session.commit()
                ret = {'message': 'Logged out'}
            else:
                ret = {'message': 'Nothing to do'}
        except Exception as e:
            db.session.rollback()
            abort(500)

        return ret, 200
