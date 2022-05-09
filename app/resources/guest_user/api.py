"""
API endpoints for "guest user" package.
"""

import datetime
import base64

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from flask_jwt_extended import create_access_token
from flasgger.utils import swag_from

from app import db, c_abort
from app.base.api import BaseResource
from app.auth.schemas import UserIdentitySchema
from app.resources.users.models import User
from app.resources.users.helpers import generate_user_random_string
from app.resources.roles import constants as ROLE
from app.resources.accounts.models import Account
from app.resources.accounts import constants as ACCOUNT
from app.base import constants as APP
from app.resources.guest_user.schemas import GuestUserSchema
from app.resources.user_settings.helpers import create_default_user_settings
from app.resources.roles.models import Role
from app.resources.unsubscriptions.helpers import create_default_unsubscription
from app.domain_resources.domains.helpers import (
    get_domain_info, get_domain_name)


# default role name for a user
DEF_ROLE = ROLE.ERT_GUEST


class GuestUserAPI(BaseResource):
    """
    Post API for managing guest users
    """

    @swag_from('swagger_docs/guest_user_post.yml')
    def post(self):
        """
        Create a guest user
        """
        guest_user_schema = GuestUserSchema()
        user_identity_schema = UserIdentitySchema()
        user_data = None
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            if 'password' not in json_data:
                json_data['password'] = base64.b64encode(
                    bytes(generate_user_random_string(size=8).encode('utf-8')))
            data, errors = guest_user_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # check user accepted terms or not
            if not data.accepted_terms:
                c_abort(422, message='Guest user not accepted terms')
            user_data = User.query.options(joinedload(
                User.profile)).filter_by(email=data.email).first()
            # if guest user already exists , return access token
            if user_data:
                # if not guest user
                if user_data.account_type != ACCOUNT.ACCT_GUEST:
                    c_abort(
                        422, message='You already have an account. Please try to login with your credentials.',
                        errors={'email': ['You already have an account. Please try to login with your credentials.']})
                else:
                    # assign current account as a account
                    user_data.current_account = user_data.account
                    result = user_identity_schema.dump(user_data)
                    expires_delta = current_app.config[
                        'JWT_ACCESS_TOKEN_EXPIRES']
                    ret = {'access_token': create_access_token(
                        identity=result.data, expires_delta=expires_delta)}
                    user_data.token_valid = True
                    user_data.last_login = datetime.datetime.utcnow()
                    db.session.add(user_data)
                    db.session.commit()
                    return ret, 200
            else:
                data = create_default_user_settings(data)
                create_default_unsubscription(data.email)
            # no errors, so add data to db
            data.created_by = 1
            data.updated_by = 1
            # sequence_id is added for ordering purpose of users
            data.sequence_id = 1
            # if role is not provided, set default role_id

            data.role_id = Role.query.filter_by(name=DEF_ROLE).first().row_id
            data.token_key = generate_user_random_string()
            if not data.account_id:
                domain_id, domain_config = get_domain_info(get_domain_name())
                account_data = Account.query.filter_by(
                    account_type=ACCOUNT.ACCT_GUEST,
                    domain_id=domain_id).first()
                data.account_type = account_data.account_type
                data.account_id = account_data.row_id
                data.profile.account_type = account_data.account_type
                data.profile.account_id = account_data.row_id

            db.session.add(data)
            db.session.commit()

            user_data = User.query.options(joinedload(
                User.profile)).filter_by(email=data.email).first()

            # assign current account as a account
            user_data.current_account = user_data.account
            result = user_identity_schema.dump(user_data)
            expires_delta = current_app.config[
                'JWT_ACCESS_TOKEN_EXPIRES']
            ret = {'access_token': create_access_token(
                identity=result.data, expires_delta=expires_delta)}
            user_data.token_valid = True
            user_data.last_login = datetime.datetime.utcnow()
            db.session.add(user_data)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (email)=(example@example.com) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return ret, 200
