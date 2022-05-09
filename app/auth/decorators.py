"""
Has the auth and permissions related decorators
"""

import datetime

import types
from functools import wraps

from flask import g, Response, request, current_app
from flask_jwt_extended import get_jwt_identity, decode_token
from flask_jwt_extended.exceptions import NoAuthorizationError
from webargs.flaskparser import parser
from flask_restful import abort
from flask_socketio import disconnect
from sqlalchemy import and_
from sqlalchemy.orm import joinedload, contains_eager

from app import c_abort, db
from app.base import constants as APP
from app.auth.schemas import ChildAccountUserSchema
from app.resources.accounts.models import Account
from app.resources.users.models import User
from app.resources.accounts import constants as ACCOUNT
from app.resources.account_user_members.models import AccountUserMember
from app.resources.login_logs.models import LoginLog


def load_current_user(func):
    """
    Simple decorator to load current_user in g object, this works only if
    called after jwt_required, due to a limitation of jwt_extended.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'current_user' in g:
            pass
        else:
            current_user = get_jwt_identity()
            current_account = None
            input_data = None
            current_date_time = datetime.datetime.utcnow()

            # for check origin from request
            '''if (not current_app.config['DEBUG'] and
                    'Origin' not in request.headers and
                    request.user_agent.platform not in
                    current_app.config['REQUEST_MOBILE_PLATFORMS']):
                raise NoAuthorizationError(
                    "You have no permission to access")
            elif (not current_app.config['DEBUG'] and
                    'Origin' in request.headers and
                    request.headers['Origin'] not in
                    current_app.config['REQUEST_ORIGINS'] and
                    request.user_agent.platform not in
                    current_app.config['REQUEST_MOBILE_PLATFORMS']):
                raise NoAuthorizationError(
                    "You have no permission to access")'''

            if current_user and 'row_id' in current_user:
                # if child account id used from query string for switch
                # account for group type user
                input_data = parser.parse(
                    ChildAccountUserSchema(), locations=('querystring',))

                if ('child_account_id' in input_data and
                        input_data['child_account_id']):
                    switched_account_id = input_data[
                        'child_account_id']
                else:
                    switched_account_id = current_user[
                        'current_account']['row_id']

                # fetch user from db and check if token_valid is False
                user = User.query.filter(
                    User.row_id == current_user['row_id']).join(
                    AccountUserMember, and_(
                        User.row_id == AccountUserMember.member_id,
                        AccountUserMember.account_id == switched_account_id
                    ), isouter=True).options(
                        contains_eager(User.membership),
                        joinedload(User.account).joinedload(Account.profile),
                        joinedload(User.role)).first()

                # if current user switched to child account, so current
                # account will be switched account
                if user.membership:
                    current_account = user.membership.account
                else:
                    # if child account id available in query string and user is
                    # not member for child account
                    if ('child_account_id' in input_data and
                            input_data['child_account_id']):
                        c_abort(
                            403, message='Child account id:' + str(
                                input_data['child_account_id']) +
                            ' is not child of' + ' current group account')
                    # if not switch account so current account is normal user
                    # account
                    else:
                        current_account = user.account

                if (not user or not user.token_valid and
                        'from_mobile' not in current_user):
                    raise NoAuthorizationError("Token invalid")
                if (not user.token_valid_mobile and
                        'from_mobile' in current_user):
                    raise NoAuthorizationError("Token invalid")

                # check random token key
                if ('token_key' not in current_user or
                        current_user['token_key'] != user.token_key and
                        request.endpoint not in
                        ['api.loginapi', 'api.designlabloginapi']  and
                        request.method != 'put'):
                    raise NoAuthorizationError("Token invalid")

                # check for guest user permission
                '''if (current_account.account_type == ACCOUNT.ACCT_GUEST and
                        request.endpoint not in
                        ACCOUNT.GU_ENDPOINT_PERMISSIONS[request.method]):
                    raise NoAuthorizationError(
                        "You have no permission to access")'''
                #if (current_account.account_type == ACCOUNT.ACCT_GUEST and
                #        request.endpoint not in
                #        ACCOUNT.GU_ENDPOINT_PERMISSIONS[request.method]):
                #    raise NoAuthorizationError(
                #        "You have no permission to access")

                # check for sell-side user permission
                #if (current_account.account_type ==
                #        ACCOUNT.ACCT_SELL_SIDE_ANALYST and
                #        request.endpoint in
                #        ACCOUNT.SELL_SIDE_ENDPOINTS_NOT_PERMISSION[
                #            request.method]):
                #    raise NoAuthorizationError(
                #        "You have no permission to access")

                # check for buy-side user permission
                #if (current_account.account_type ==
                #        ACCOUNT.ACCT_BUY_SIDE_ANALYST and
                #        request.endpoint in
                #        ACCOUNT.BUY_SIDE_ENDPOINTS_NOT_PERMISSION[
                #            request.method]):
                #    raise NoAuthorizationError(
                #        "You have no permission to access")

                # check for general investor user permission
                #if (current_account.account_type ==
                #        ACCOUNT.ACCT_GENERAL_INVESTOR and
                #        request.endpoint in
                #        ACCOUNT.GENERAL_INVESTOR_ENDPOINTS_NOT_PERMISSION[
                #            request.method]):
                #    raise NoAuthorizationError(
                #        "You have no permission to access")

                # check for corporate user permissions
                '''if (current_account.account_type == ACCOUNT.ACCT_CORPORATE and
                        request.endpoint in
                        ACCOUNT.CORPORATE_ENDPOINTS_PREMIUM_PERMISSION[
                        request.method]):
                    if (not current_account.subscription_start_date or
                            not current_account.subscription_end_date or
                            current_date_time <
                            current_account.subscription_start_date or
                            current_date_time >
                            current_account.subscription_end_date):
                        c_abort(403, message='Your subscription has expired',
                                errors={'extra_code': APP.EC_SUB_EXPIRED})'''

                # check for private user permissions
                if (current_account.account_type == ACCOUNT.ACCT_PRIVATE and
                        request.endpoint in
                        ACCOUNT.PRIVATE_ENDPOINTS_PREMIUM_PERMISSION[
                            request.method]):
                    if (not current_account.subscription_start_date or
                            not current_account.subscription_end_date or
                            current_date_time <
                            current_account.subscription_start_date or
                            current_date_time >
                            current_account.subscription_end_date):
                        c_abort(403,
                                message='Your subscription has expired',
                                errors={
                                    'extra_code': APP.EC_SUB_EXPIRED})

                # check for sme user permissions
                if (current_account.account_type == ACCOUNT.ACCT_SME and
                        request.endpoint in
                        ACCOUNT.SME_ENDPOINTS_PREMIUM_PERMISSION[
                            request.method]):
                    if (not current_account.subscription_start_date or
                            not current_account.subscription_end_date or
                            current_date_time <
                            current_account.subscription_start_date or
                            current_date_time >
                            current_account.subscription_end_date):
                        c_abort(403,
                                message='Your subscription has expired',
                                errors={
                                    'extra_code': APP.EC_SUB_EXPIRED})

                # check for corporate group user permissions
                if (current_account.account_type == ACCOUNT.ACCT_CORP_GROUP and
                        request.endpoint in
                        ACCOUNT.CORP_GROUP_ENDPOINTS_PERMIUM_PERMISSION[
                        request.method]):
                    if (not current_account.subscription_start_date or
                            not current_account.subscription_end_date or
                            current_date_time <
                            current_account.subscription_start_date or
                            current_date_time >
                            current_account.subscription_end_date):
                        c_abort(403,
                                message='Your subscription has expired',
                                errors={
                                    'extra_code': APP.EC_SUB_EXPIRED})

                # add account, permission info for use in various function
                current_user['primary_account_id'] = user.account.row_id
                current_user['account_id'] = current_account.row_id
                current_user['account_profile_id'] = \
                    current_account.profile.row_id
                if user.role:
                    current_user['role']['permissions'] = user.role.permissions
                # 'account' key already added in identity schema,
                # so we are adding 'account_model'
                # 'account_model' is using for search_privacy in user_profile
                current_user['account_model'] = user.account
                # for unread notification count of current user,
                # its use in notification get list api
                current_user['current_notification_count'] = \
                    user.current_notification_count
                current_user['current_notification_designlab_count'] = \
                    user.current_notification_designlab_count
                g.current_user = current_user
                log_id = current_user.get('login_log_id')
                if log_id:
                    LoginLog.query.filter_by(row_id=log_id).update(
                        {'last_active_time': current_date_time},
                        synchronize_session=False)
                    db.session.commit()

        return func(*args, **kwargs)

    return wrapper


def socket_authenticated_only(func):
    """
    Simple decorator to verify login and load current_user in g object
    for sockets.
    """
    @wraps(func)
    def wrapped(*args, **kwargs):
        if 'current_user' in g:
            pass
        else:
            # loop the arguments
            access_token = ''
            for arg in args:
                try:
                    if arg and 'access_token' in arg:
                        access_token = arg['access_token']
                except Exception as e:
                    continue
            if not access_token:
                try:
                    if 'access_token' in kwargs:
                        access_token = kwargs['access_token']
                except Exception as e:
                    pass
            if not access_token:
                for kwarg in kwargs:
                    try:
                        if kwarg and 'access_token' in kwarg:
                            access_token = kwarg['access_token']
                    except Exception as e:
                        continue
            decoded = ''
            if access_token:
                decoded = decode_token(access_token)
            current_user = None
            if decoded and 'identity' in decoded:
                current_user = decoded['identity']
            if current_user and 'row_id' in current_user:
                # fetch user from db and check if token_valid is False
                user = User.query.options(joinedload(
                    User.account), joinedload(User.role)).get(
                    current_user['row_id'])

                if (not user or not user.token_valid and
                        'from_mobile' not in current_user):
                    disconnect()
                    # raise NoAuthorizationError("Token invalid")
                if (not user.token_valid_mobile and
                        'from_mobile' in current_user):
                    disconnect()
                    # raise NoAuthorizationError("Token invalid")

                # add account, permission info for use in various function
                current_user['account_id'] = user.account.row_id
                current_user['role']['permissions'] = user.role.permissions
                g.current_user = current_user
            else:
                disconnect()

        return func(*args, **kwargs)
    return wrapped


def role_permission_required(perms=None, menus=None, roles=None):
    def role_permission_required_inner(f):
        """
        Decorator to check for permissions, and menu access permissions of the
        current user
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_user = g.current_user
            if current_user is None or not current_user:
                abort(401)
            # check user -> role -> permissions
            if perms and not isinstance(perms, types.FunctionType):
                # user has no role!
                if not current_user['role']:
                    abort(403)
                # user has perms
                for p in perms:
                    if p not in current_user['role']['permissions']:
                        abort(403)
            # check user -> role -> menu_items
            if menus and not isinstance(menus, types.FunctionType):
                # user has no role!
                if not current_user['role']:
                    abort(403)
                # user has menu access
                for p in menus:
                    if p not in current_user['role']['menu_items']:
                        abort(403)
            # check user -> role
            if roles and not isinstance(roles, types.FunctionType):
                # user has no role!
                if not current_user['role']:
                    abort(403)
                # user has any one of the roles
                if current_user['role']['name'] not in roles:
                    abort(403)

            return f(*args, **kwargs)
        return decorated_function

    if isinstance(perms, types.FunctionType):
        return role_permission_required_inner(perms)

    return role_permission_required_inner


def requires_basic_auth(f):
    """
    Decorator to require HTTP Basic Auth for flasgger endpoint.
    """

    def check_auth(email, password):
        if email and password:
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                return True
        return False

    def authenticate():
        return Response(
            "Authentication required.", 401,
            {"WWW-Authenticate": "Basic realm='Login Required'"})

    @wraps(f)
    def decorated(*args, **kwargs):

        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)

    return decorated
