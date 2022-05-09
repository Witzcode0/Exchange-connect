"""
API endpoints for "auth" package.
"""

import datetime

from werkzeug.exceptions import HTTPException
from flask import request, current_app, g
from webargs.flaskparser import parser
from flask_restful import abort
from flask_jwt_extended import (
    create_access_token, jwt_required, decode_token)
from flask_jwt_extended.exceptions import JWTDecodeError
from jwt.exceptions import DecodeError
from marshmallow.exceptions import ValidationError
from flasgger.utils import swag_from
from sqlalchemy import and_, any_, func
from sqlalchemy.orm import joinedload

from app import db, c_abort
from app.base.api import load_current_user, BaseResource
from app.resources.users.models import User
from app.resources.users.helpers import generate_user_random_string
from app.resources.accounts import constants as ACCOUNT
from app.auth.schemas import (
    LoginSchema, UserIdentitySchema, EmailSchema, ResetPasswordSchema,
    TokenVerificationSchema, UserLoginReadArgsSchema, SwitchAccountUserSchema)
from app.auth.helpers import (
    generate_password_reset_link, verify_password_reset_link,
    send_password_reset_link, send_designlab_password_reset_link)
from app.resources.account_user_members.models import AccountUserMember
from app.resources.user_settings.models import UserSettings
from app.resources.user_settings import constants as USERSET
from app.resources.users import constants as USER
from app.resources.login_logs.models import LoginLog
from app.resources.login_logs.helpers import insert_login_log
from app.domain_resources.domains.helpers import (
    get_domain_name, get_domain_info)


class LoginAPI(BaseResource):
    """
    API to login/logout users
    """

    @swag_from('swagger_docs/login_post.yml')
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
            login = parser.parse(
                UserLoginReadArgsSchema(), locations=('querystring',))
            data, errors = login_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            user = User.query.options(joinedload(
                User.profile)).filter_by(email=data['email']).first()
            if not user or user.account_type == ACCOUNT.ACCT_GUEST:
                c_abort(401, message='Invalid Username or Password')

            if user.deactivated is True or user.deleted is True:
                c_abort(403, message='User is Deactivated, '
                                     'Please Contact to Administrator')

            if user.unverified:
                c_abort(403, message='Email not verified. Please verify or '
                                     'contact administrator.')

            if user.login_locked:
                c_abort(401, message='Your account has been locked, '
                        'you\'ve exceeded the number of login attempts. '
                        'Please go to Forgot Password to reset again.')
            if user.only_design_lab:
                c_abort(403, message="Unauthorized")
            domain_name = get_domain_name()
            domain_id, domain_config = get_domain_info(domain_name)
            if user.account.domain_id != domain_id:
                c_abort(401, message='Please login to {}'.format(
                    user.account.domain.name))
            if user.account.blocked:
                c_abort(401, message='Your account has been blocked. '
                                     'Please contact administrator.')
            if not user.check_password(data['password']):
                if not user.login_locked:
                    user.unsuccessful_login_count += 1
                    db.session.add(user)
                    db.session.commit()
                c_abort(401, message='Invalid Username or Password')
            else:
                expires_delta = current_app.config[
                    'JWT_ACCESS_TOKEN_EXPIRES']

            if login and 'from_mobile' in login:
                user.token_valid_mobile = True
                user.from_mobile = True
                # for push notification add and remove requested device id
                if ('device_request_id' in data and
                        data['device_request_id'] and
                        request.user_agent.platform ==
                        USERSET.MOB_ANDROID):
                    # remove device from other users
                    UserSettings.query.filter(
                        data['device_request_id'] == any_(
                            UserSettings.android_request_device_ids)
                    ).update(
                        {UserSettings.android_request_device_ids:
                            func.array_remove(
                                UserSettings.android_request_device_ids,
                                data['device_request_id'])},
                        synchronize_session=False)
                    db.session.commit()
                    # add device for current user
                    UserSettings.query.filter(
                       UserSettings.user_id == user.row_id).update({
                                UserSettings.android_request_device_ids:
                                func.array_append(
                                    UserSettings.android_request_device_ids,
                                    data['device_request_id'])},
                        synchronize_session=False)
                    db.session.commit()
                # for ios mobile device
                if ('device_request_id' in data and
                        data['device_request_id'] and
                        request.user_agent.platform == USERSET.MOB_IOS):
                    # remove device from other users
                    UserSettings.query.filter(
                        data['device_request_id'] == any_(
                            UserSettings.ios_request_device_ids)
                    ).update(
                        {UserSettings.ios_request_device_ids:
                            func.array_remove(
                                UserSettings.ios_request_device_ids,
                                data['device_request_id'])},
                        synchronize_session=False)
                    db.session.commit()
                    # add device for current user
                    UserSettings.query.filter(
                        UserSettings.user_id == user.row_id).update({
                            UserSettings.ios_request_device_ids:
                            func.array_append(
                                UserSettings.ios_request_device_ids,
                                data['device_request_id'])},
                        synchronize_session=False)
                    db.session.commit()

                expires_delta = current_app.config[
                    'JWT_ACCESS_TOKEN_EXPIRES_MOBILE']
            # assign current account as a account
            user.current_account = user.account
            result = identity_schema.dump(user)
            log_id = insert_login_log(request, user)
            result.data['login_log_id'] = log_id
            ret = {'access_token': create_access_token(
                identity=result.data, expires_delta=expires_delta)}
            if 'from_mobile' not in login:
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
    @swag_from('swagger_docs/login_put.yml')
    def put(self):
        """
        Refresh token
        """
        identity_schema = UserIdentitySchema()
        ret = {}
        try:
            user = User.query.get(g.current_user['row_id'])

            if user and (user.deactivated is True or user.deleted is True):
                c_abort(403, message='User is Deactivated, '
                                     'Please Contact to Administrator')

            if user and user.unverified:
                c_abort(403, message='Email not verified. Please verify or '
                                     'contact administrator.')

            if user:
                expires_delta = current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
                if 'from_mobile' in g.current_user:
                    expires_delta = current_app.config[
                        'JWT_ACCESS_TOKEN_EXPIRES_MOBILE']
                    user.from_mobile = True
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
    @swag_from('swagger_docs/login_delete.yml')
    def delete(self):
        """
        Logout user
        """
        ret = {}
        login = None
        try:
            login = parser.parse(
                UserLoginReadArgsSchema(), locations=('querystring',))
            user = User.query.get(g.current_user['row_id'])

            if not user:
                ret = {'message': 'Nothing to do'}

            if login and 'from_mobile' in login:
                user.token_valid_mobile = False
            else:
                user.token_valid = False
            current_time = datetime.datetime.utcnow()
            user.last_logout = current_time
            LoginLog.query.filter_by(
                row_id=g.current_user.get('login_log_id')).update(
                {'logout_time': current_time},
                synchronize_session=False)
            db.session.add(user)
            db.session.commit()
            ret = {'message': 'Logged out'}

        except Exception as e:
            db.session.rollback()
            abort(500)

        return ret, 200


class DesignLabLoginAPI(BaseResource):
    """
    API to login/logout users
    """

    @swag_from('swagger_docs/login_post.yml')
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
            login = parser.parse(
                UserLoginReadArgsSchema(), locations=('querystring',))
            data, errors = login_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            user = User.query.options(joinedload(
                User.profile)).filter_by(email=data['email']).first()
            if not user:
                c_abort(401, message='Invalid Username or Password')

            if user.account_type != ACCOUNT.ACCT_CORPORATE:
                c_abort(403, message="Only corporate users can login here.")

            if user.deactivated is True or user.deleted is True:
                c_abort(403, message='User is Deactivated, '
                                     'Please Contact to Administrator')

            if user.unverified:
                c_abort(403, message='Email not verified. Please verify or '
                                     'contact administrator.')

            if user.login_locked:
                c_abort(401, message='Your account has been locked, '
                        'you\'ve exceeded the number of login attempts. '
                        'Please go to Forgot Password to reset again.')

            if user.account.blocked:
                c_abort(401, message='Your account has been blocked. '
                                     'Please contact administrator.')
            if not user.check_password(data['password']):
                if not user.login_locked:
                    user.unsuccessful_login_count += 1
                    db.session.add(user)
                    db.session.commit()
                c_abort(401, message='Invalid Username or Password')
            else:
                expires_delta = current_app.config[
                    'JWT_ACCESS_TOKEN_EXPIRES']

            if login and 'from_mobile' in login:
                user.token_valid_mobile = True
                user.from_mobile = True
                # for push notification add and remove requested device id
                if ('device_request_id' in data and
                        data['device_request_id'] and
                        request.user_agent.platform ==
                        USERSET.MOB_ANDROID):
                    # remove device from other users
                    UserSettings.query.filter(
                        data['device_request_id'] == any_(
                            UserSettings.android_request_device_ids)
                    ).update(
                        {UserSettings.android_request_device_ids:
                            func.array_remove(
                                UserSettings.android_request_device_ids,
                                data['device_request_id'])},
                        synchronize_session=False)
                    db.session.commit()
                    # add device for current user
                    UserSettings.query.filter(
                       UserSettings.user_id == user.row_id).update({
                                UserSettings.android_request_device_ids:
                                func.array_append(
                                    UserSettings.android_request_device_ids,
                                    data['device_request_id'])},
                        synchronize_session=False)
                    db.session.commit()
                # for ios mobile device
                if ('device_request_id' in data and
                        data['device_request_id'] and
                        request.user_agent.platform == USERSET.MOB_IOS):
                    # remove device from other users
                    UserSettings.query.filter(
                        data['device_request_id'] == any_(
                            UserSettings.ios_request_device_ids)
                    ).update(
                        {UserSettings.ios_request_device_ids:
                            func.array_remove(
                                UserSettings.ios_request_device_ids,
                                data['device_request_id'])},
                        synchronize_session=False)
                    db.session.commit()
                    # add device for current user
                    UserSettings.query.filter(
                        UserSettings.user_id == user.row_id).update({
                            UserSettings.ios_request_device_ids:
                            func.array_append(
                                UserSettings.ios_request_device_ids,
                                data['device_request_id'])},
                        synchronize_session=False)
                    db.session.commit()

                expires_delta = current_app.config[
                    'JWT_ACCESS_TOKEN_EXPIRES_MOBILE']
            # assign current account as a account
            user.current_account = user.account
            result = identity_schema.dump(user)
            ret = {'access_token': create_access_token(
                identity=result.data, expires_delta=expires_delta)}
            if 'from_mobile' not in login:
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
    @swag_from('swagger_docs/login_put.yml')
    def put(self):
        """
        Refresh token
        """
        identity_schema = UserIdentitySchema()
        ret = {}
        try:
            user = User.query.get(g.current_user['row_id'])

            if user and (user.deactivated is True or user.deleted is True):
                c_abort(403, message='User is Deactivated, '
                                     'Please Contact to Administrator')

            if user and user.unverified:
                c_abort(403, message='Email not verified. Please verify or '
                                     'contact administrator.')

            if user:
                expires_delta = current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
                if 'from_mobile' in g.current_user:
                    expires_delta = current_app.config[
                        'JWT_ACCESS_TOKEN_EXPIRES_MOBILE']
                    user.from_mobile = True
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
    @swag_from('swagger_docs/login_delete.yml')
    def delete(self):
        """
        Logout user
        """
        ret = {}
        login = None
        try:
            login = parser.parse(
                UserLoginReadArgsSchema(), locations=('querystring',))
            user = User.query.get(g.current_user['row_id'])

            if user:
                if login and 'from_mobile' in login:
                    user.token_valid_mobile = False
                else:
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


class ForgotPasswordAPI(BaseResource):
    """
    for forgot password
    """

    @swag_from('swagger_docs/forgotpass_post.yml')
    def post(self):
        """
        Generate link for reset password and send email
        """
        email_schema = EmailSchema()
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        ret = ''
        try:
            data, errors = email_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            user = User.query.filter_by(email=data['email']).first()
            if not user or user.account_type == ACCOUNT.ACCT_GUEST:
                c_abort(404, message='Bad email')
            if user.unverified:
                c_abort(403, message='Email not verified. Please verify or '
                                     'contact administrator.')

            domain_name = get_domain_name()
            domain_id, domain_config = get_domain_info(domain_name)
            url = generate_password_reset_link(user, domain_config)
            message, errors = send_password_reset_link(user, url)
            if errors:
                c_abort(422, errors=errors)
            ret = message

        except ValidationError as e:
            c_abort(422, errors=e.messages)
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': ret}, 200

    @swag_from('swagger_docs/forgotpass_put.yml')
    def put(self, token):
        """
        for update password
        :param token: reset password link
        """
        password_schema = ResetPasswordSchema()
        try:
            user = None
            email = verify_password_reset_link(token)

            if email:
                user = User.query.filter_by(email=email).first()

            if not user:
                c_abort(404, message='Bad email')
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            data, errors = password_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            user.password = data.password
            user.token_key = generate_user_random_string()
            # if user will change password, so unsuccessful login count will
            # be zero
            user.unsuccessful_login_count = 0
            db.session.add(user)
            db.session.commit()
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Password successfully changed'}, 200


class DesignLabForgotPasswordAPI(BaseResource):
    """
    for forgot password
    """

    # @swag_from('swagger_docs/forgotpass_post.yml')
    def post(self):
        """
        Generate link for reset password and send email
        """
        email_schema = EmailSchema()
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        ret = ''
        try:
            data, errors = email_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            user = User.query.filter_by(email=data['email']).first()
            if not user or user.account_type != ACCOUNT.ACCT_CORPORATE:
                c_abort(404, message='Bad email')
            if user.unverified:
                c_abort(403, message='Email not verified. Please verify or '
                                     'contact administrator.')

            url = generate_password_reset_link(
                user, current_app.config['DESIGNLAB_CONFIG'])
            message, errors = send_designlab_password_reset_link(user, url)
            if errors:
                c_abort(422, errors=errors)
            ret = message

        except ValidationError as e:
            c_abort(422, errors=e.messages)
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': ret}, 200

    # @swag_from('swagger_docs/forgotpass_put.yml')
    def put(self, token):
        """
        for update password
        :param token: reset password link
        """
        password_schema = ResetPasswordSchema()
        try:
            user = None
            email = verify_password_reset_link(token)

            if email:
                user = User.query.filter_by(email=email).first()

            if not user:
                c_abort(404, message='Bad email')
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            data, errors = password_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            user.password = data.password
            user.token_key = generate_user_random_string()
            # if user will change password, so unsuccessful login count will
            # be zero
            user.unsuccessful_login_count = 0
            db.session.add(user)
            db.session.commit()
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Password successfully changed'}, 200


class TokenVerificationAPI(BaseResource):
    """
    API for verification if user can access ownership analysis,
    disclosure enhancement and investor targeting
    """

    @swag_from('swagger_docs/token_verification.yml')
    def post(self):
        """
        pass authentication token and check user have access or not
        """
        verification_schema = TokenVerificationSchema()
        json_data = request.get_json()
        if not json_data:
            return c_abort(400)

        try:
            data, errors = verification_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            '''if 'user_token' in data and data['user_token']:
                try:
                    user_identity = decode_token(data['user_token'])
                except Exception as e:
                    if not isinstance(e, DecodeError) and not isinstance(
                            e, JWTDecodeError):
                        current_app.logger.exception(e)
                    c_abort(401, message='Invalid token')
                if user_identity:
                    user_account_type =\
                        user_identity['identity']['account']['account_type']
                    account_name = \
                        user_identity['identity']['account']['account_name']
                    if (user_account_type not in [
                        ACCOUNT.ACCT_CORPORATE, ACCOUNT.ACCT_CORP_GROUP,
                        ACCOUNT.ACCT_SELL_SIDE_ANALYST,
                        ACCOUNT.ACCT_BUY_SIDE_ANALYST,
                        ACCOUNT.ACCT_GENERAL_INVESTOR] and
                            account_name != 'Default'):
                        c_abort(403,
                                message='User does not have permission to '
                                        'access Ownership Analysis, '
                                        'Investor Targeting and '
                                        'Disclosures Enhancement')
            else:
                c_abort(422, message='No input provided')'''
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Access permission approved'}, 200


class SwitchAccountUserLoginAPI(BaseResource):
    """
    API to switch account for group account user
    """

    @jwt_required
    @load_current_user
    def put(self):
        """
        :return:
        """
        switch_account_schema = SwitchAccountUserSchema()
        identity_schema = UserIdentitySchema()
        ret = {}

        try:
            user = User.query.get(g.current_user['row_id'])

            if user and (user.deactivated is True or user.deleted is True):
                c_abort(403, message='User is Deactivated, '
                                     'Please Contact to Administrator')

            if user and user.unverified:
                c_abort(403, message='Email not verified. Please verify or '
                                     'contact administrator.')

            if user and user.account_type != ACCOUNT.ACCT_CORP_GROUP:
                c_abort(403, message='User is not group type')

            # get the json data from the request
            json_data = request.get_json()
            if not json_data:
                c_abort(400)
            if user:
                switch_account_data, errors = switch_account_schema.load(
                    json_data)
                if errors:
                    c_abort(422, errors=errors)

                expires_delta = current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
                if 'from_mobile' in g.current_user:
                    expires_delta = current_app.config[
                        'JWT_ACCESS_TOKEN_EXPIRES_MOBILE']
                    user.from_mobile = True
                # check current user exists in user member for switch account
                # id
                account_member = AccountUserMember.query.filter(and_(
                        AccountUserMember.member_id == User.row_id,
                        AccountUserMember.account_id ==
                        switch_account_data['child_account_id'])).first()

                if not account_member:
                    c_abort(
                        403, message='Child account id:' + str(
                            switch_account_data['child_account_id']) +
                        ' is not child of' + ' current group account')
                user.current_account = account_member.account
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
