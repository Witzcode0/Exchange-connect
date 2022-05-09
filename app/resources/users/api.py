"""
API endpoints for "user" package.
"""

import datetime
import base64

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.sql.expression import case
from sqlalchemy.inspection import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only, joinedload
from sqlalchemy import func, and_
from flasgger.utils import swag_from

from app import db, c_abort
from app.base import constants as APP
from app.base.api import AuthResource
from app.auth.decorators import role_permission_required
from app.resources.users.models import User
from app.resources.user_profiles.models import UserProfile
from app.resources.accounts import constants as ACCOUNT
from app.resources.users.schemas import (
    UserSchema, UserListSchema, UserReadArgsSchema, ChangePasswordSchema,
    FirstTimeChangePasswordSchema, UserEditSchema, UserOrderSchema,
    AdminUserOrderSchema)
from app.resources.user_profiles.schemas import UserProfileSchema
from app.resources.users.helpers import (
    check_account_membership, check_role_allowed, generate_user_random_string,
    check_users_exist_for_account, add_registration_request_for_user)
from app.resources.user_settings.schemas import UserSettingsSchema
from app.resources.roles import constants as ROLE
from app.resources.roles.models import Role
from app.resources.accounts.models import Account
from app.resources.accounts.helpers import transfer_account_object
from app.resources.account_profiles.models import AccountProfile
from app.resources.account_managers.models import AccountManager
from app.resources.user_settings.helpers import create_default_user_settings
from app.resources.contacts.helpers import create_default_contacts
from app.resources.registration_requests.helpers import \
    link_new_user_to_invitee
from app.resources.account_user_members.helpers import \
    add_user_member_for_child_accounts
from app.resources.unsubscriptions.helpers import create_default_unsubscription
from app.resources.unsubscriptions.models import Unsubscription
from app.resources.unsubscriptions.schemas import UnsubscriptionSchema

from queueapp.user_email_tasks import (
    send_password_change_email, designlab_send_password_change_email)
from queueapp.accounts.account_stats_tasks import update_account_stats


# default role name for a user
DEF_ROLE = ROLE.ERT_NO


class UserAPI(AuthResource):
    """
    CRUD API for managing users by admins
    """

    @role_permission_required(perms=[ROLE.EPT_NU], roles=[
        ROLE.ERT_SU, ROLE.ERT_MNG])
    def post(self):
        """
        Create a user
        """

        user_schema = UserSchema()
        user_profile_schema = UserProfileSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            user_model = None
            updated_account_id = False
            if 'email' in json_data:
                user_model = User.query.filter_by(
                    email=json_data['email']).first()
            # if guest user already exists
            if user_model and user_model.account_type == ACCOUNT.ACCT_GUEST:
                password = None
                if 'password' in json_data:
                    password = json_data['password']
                    del json_data['password']
                data_profile, errors = user_profile_schema.load(
                    json_data['profile'], instance=user_model.profile,
                    partial=True)
                if errors:
                    return c_abort(422, errors=errors)

                json_data.pop('profile')
                data, errors = user_schema.load(
                    json_data, instance=user_model, partial=True)
                if errors:
                    return c_abort(422, errors=errors)
                # no errors, so add data to db
                if password and not data.check_password(password):
                    # new password is sent as non-empty
                    data.set_password(password)
                    data.token_key = generate_user_random_string()
                updated_account_id = True
            else:
                # if admin want to user as a register request but not send
                # password, so set password
                if ('is_registration_request' in json_data and
                        json_data['is_registration_request'] and
                        'password' not in json_data):
                    json_data['password'] = base64.b64encode(
                        bytes(generate_user_random_string().encode(
                            'utf-8')))
                data, errors = user_schema.load(json_data)
                if errors:
                    c_abort(422, errors=errors)

            if not data.accepted_terms:
                c_abort(422, message='User not accepted terms')
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            data.token_key = generate_user_random_string()
            data = create_default_user_settings(data)

            # if role is not provided, set default role_id
            if not data.role_id:
                role_id = Role.query.filter_by(name=DEF_ROLE).first().row_id
                data.role_id = role_id
            if (not data.account_type or
                    data.account_type == ACCOUNT.ACCT_GUEST):
                account_type = Account.query.filter_by(
                    row_id=data.account_id).first().account_type
                data.account_type = account_type
                data.profile.account_type = account_type
                data.profile.account_id = data.account_id
            # check account membership and check user role
            if not check_account_membership(data):
                abort(403)
            # check role assigned
            if not check_role_allowed(data):
                abort(403)
            # add account activation date
            account = Account.query.filter_by(
                row_id=data.account_id).first()
            if not check_users_exist_for_account(data.account_id):
                account.activation_date = datetime.datetime.utcnow()
                if not account.subscription_start_date:
                    account.subscription_start_date = \
                        datetime.datetime.utcnow()
                    account.is_trial = True
                if not account.subscription_end_date:
                    account.subscription_end_date = \
                        account.subscription_start_date + current_app.config[
                            'DEF_TRIAL_PERIOD']
                    account.is_trial = True
                db.session.add(account)
            # fetch the users associated with the account
            # and get the highest in order sequence_id
            last_in_order_user = User.query.filter_by(
                account_id=data.account_id).order_by(
                User.sequence_id.desc()).first()
            if last_in_order_user:
                last_in_order_sequence_id = last_in_order_user.sequence_id
                # assign the sequence_id as new highest in order sequence_id
                data.sequence_id = last_in_order_sequence_id + 1
            else:
                data.sequence_id = 1
            db.session.add(data)
            db.session.commit()
            # if admin want to create registration request for created user
            if data.is_registration_request:
                data.unverified = True
                add_registration_request_for_user(data, account.domain_id)

            # if account is group type so add user member for all child account
            # of particular group type account
            if account.account_type == ACCOUNT.ACCT_CORP_GROUP:
                add_user_member_for_child_accounts(
                    data.row_id, data.account_id, data.is_admin)
            # create default contacts
            create_default_contacts(data.row_id)
            link_new_user_to_invitee(data.row_id, data.email)
            # create default unsubscription for user
            create_default_unsubscription(data.email)
            # if account_id change for guest user
            if updated_account_id:
                transfer_account_object(data.row_id, data.account_id)
            # for update account stats
            update_account_stats.s(True, data.account_id).delay()
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

        return {'message': 'User Added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @role_permission_required(perms=[ROLE.EPT_NU], roles=[
        ROLE.ERT_SU, ROLE.ERT_MNG])
    @swag_from('swagger_docs/user_put.yml')
    def put(self, row_id):
        """
        Update a user
        """

        user_edit_schema = UserEditSchema()
        user_profile_schema = UserProfileSchema()
        user_setting_schema = UserSettingsSchema()
        unsubscription_schema = UnsubscriptionSchema()
        # first find model
        model = None
        try:
            model = User.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='User id: %s does not exist' %
                                     str(row_id))
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
            password = None
            data_profile = None
            user_setting = {}
            unverified = True
            unsubscriptions = None
            if 'unverified' in json_data:
                unverified = json_data.pop('unverified')
            if 'deactivated' in json_data and json_data['deactivated'] is True:
                model.token_valid = False
                model.token_valid_mobile = False
            if 'password' in json_data:
                password = base64.b64decode(
                    json_data['password']).decode('utf-8')
                del json_data['password']
            if 'settings' in json_data and json_data['settings']:
                user_setting = json_data.pop('settings')
            if 'unsubscriptions' in json_data:
                unsubscriptions = json_data.pop('unsubscriptions')
            # validate and deserialize input
            # for update user profile details
            if 'profile' in json_data:
                data_profile, errors = user_profile_schema.load(
                    json_data['profile'], instance=model.profile, partial=True)
                if errors:
                    err = {'profile': errors}
                    c_abort(422, errors=err)
                json_data.pop('profile')
            # for update user details
            data, errors = user_edit_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            if password and not data.check_password(password):
                # new password is sent as non-empty
                data.set_password(password)
                data.token_key = generate_user_random_string()
            if password:
                data.unsuccessful_login_count = 0
            # if setting not there for particular user, so set default
            # user settings
            if not data.settings:
                data = create_default_user_settings(data)
            if data_profile:
                data.profile = data_profile
            data.updated_by = g.current_user['row_id']
            if user_setting:
                setting_data, errors = user_setting_schema.load(
                    user_setting, instance=model.settings, partial=True)
                if errors:
                    c_abort(422, errors=errors)
            if unsubscriptions is not None:
                unsubscription_data, errors = unsubscription_schema.load(
                    unsubscriptions, instance=model.unsubscriptions,
                    partial=True)
                if errors:
                    c_abort(422, errors=errors)
            # check account membership and check user role
            if not check_account_membership(data):
                abort(403)
            # check role assigned
            if not check_role_allowed(data):
                abort(403)

            if not unverified:
                data.unverified = unverified
            db.session.add(data)
            db.session.commit()
            # for update account stats
            update_account_stats.s(True, data.account_id).delay()
        except HTTPException as e:
            raise e
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (name)=(example@example.com) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except Forbidden as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Updated User id: %s' % str(row_id)}, 200

    @role_permission_required(perms=[ROLE.EPT_NU], roles=[
        ROLE.ERT_SU, ROLE.ERT_MNG])
    def delete(self, row_id):
        """
        Delete a user
        """

        model = None
        try:
            # first find model
            model = User.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='User id: %s does not exist' %
                                     str(row_id))
            # if model is found, and not yet deleted, delete it
            model.deleted = True
            # check account membership and check user role
            if not check_account_membership(model):
                abort(403)
            db.session.add(model)
            db.session.commit()
            # for update account stats
            update_account_stats.s(True, model.account_id).delay()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204

    @role_permission_required(perms=[ROLE.EPT_NU], roles=[
        ROLE.ERT_SU, ROLE.ERT_MNG])
    def get(self, row_id):
        """
        Get a user by id
        """

        model = None
        try:
            # first find model
            model = db.session.query(User).join(
                Unsubscription, Unsubscription.email == User.email,
                isouter=True).filter(User.row_id == row_id).first()
            if model is None or model.deleted:
                c_abort(404, message='User id: %s does not exist' %
                                     str(row_id))
            # check account membership and check user role
            if not check_account_membership(model):
                abort(403)
            result = UserSchema(
                exclude=UserSchema._default_exclude_fields).dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class UserListAPI(AuthResource):
    """
    Read API for user lists, i.e, more than 1 user
    """

    model_class = User

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['profile', 'role', 'account']
        super(UserListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        is_registration_request = None
        account_type = None
        # in case of account manager he might need other users
        need_admins = filters.pop('need_admins', False)
        role_names = filters.pop('role_names', [])
        if 'is_registration_request' in filters:
            is_registration_request = filters.pop('is_registration_request')
        if 'account_type' in filters and filters['account_type']:
            account_type = filters.pop('account_type')

        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)
        sector_id = extra_query.pop('sector_id', None)
        industry_id = extra_query.pop('industry_id', None)
        # build specific extra queries filters
        if extra_query:
            for f in extra_query:
                if f == 'designation' and extra_query['designation']:
                    query_filters['filters'].append(func.lower(
                        UserProfile.designation).like(
                        '%' + filters[f].lower() + '%'))
                if f == 'account_name' and extra_query[
                        'account_name']:
                    query_filters['filters'].append(func.lower(
                        Account.account_name).like(
                        '%' + filters[f].lower() + '%'))
            if 'full_name' in extra_query and extra_query['full_name']:
                full_name = '%' + (extra_query["full_name"]).lower() + '%'
                query_filters['filters'].append(func.concat(
                    func.lower(UserProfile.first_name), ' ',
                    func.lower(UserProfile.last_name)).like(full_name))
            if 'role_name' in extra_query and extra_query['role_name']:
                query_filters['filters'].append(
                    func.lower(Role.name).like(
                        '%' + extra_query['role_name'].lower() + '%'))

        # add membership filter if not a super-admin/admin user
        if g.current_user['role']['name'] not in [
                ROLE.ERT_SU, ROLE.ERT_AD, ROLE.ERT_MNG, ROLE.ERT_CA]:
            query_filters['base'].append(
                User.account_id == g.current_user['account_id'])
        # filter by registration request
        if is_registration_request:
            query_filters['base'].append(
                User.is_registration_request == is_registration_request)
        # filter by account type
        if not account_type:
            query_filters['base'].append(
                User.account_type != ACCOUNT.ACCT_GUEST)
        else:
            query_filters['base'].append(
                and_(User.account_type == account_type))
        # for not getting default account type users
        query_filters['base'].append(Account.account_name != 'Default')

        if 'account_name' in sort['sort_by']:
            mapper = inspect(Account)
        elif any(key in sort['sort_by'] for key in [
                'first_name', 'last_name', 'designation']):
            mapper = inspect(UserProfile)
        else:
            mapper = inspect(User)
        if sort:
            sort_fxn = 'asc'
            if sort['sort'] == 'dsc':
                sort_fxn = 'desc'
            for sby in sort['sort_by']:
                if sby in mapper.columns:
                    order.append(getattr(mapper.columns[sby], sort_fxn)())

        query = self._build_final_query(
            query_filters, query_session, operator,
            apply_domain_filter=extra_query['apply_domain_filter'])
        query = query.join(
            AccountProfile, User.account_id == AccountProfile.account_id).join(
            UserProfile, UserProfile.user_id == User.row_id).join(
            Account).options(
            joinedload(User.account), joinedload(User.role),
            joinedload(User.profile).load_only('first_name', 'last_name'))
        # manager can access assigned account users only
        if g.current_user['role']['name'] == ROLE.ERT_MNG and not need_admins:
            query = query.join(
                AccountManager, and_(
                    User.account_id == AccountManager.account_id,
                    AccountManager.manager_id == g.current_user['row_id']))

        if sector_id:
            query = query.filter(AccountProfile.sector_id == sector_id)
        if industry_id:
            query = query.filter(AccountProfile.industry_id == industry_id)
        if role_names:
            query = query.join(Role).filter(Role.name.in_(role_names))
        return query, db_projection, s_projection, order, paging

    @role_permission_required(perms=[ROLE.EPT_NU], roles=[
        ROLE.ERT_SU, ROLE.ERT_MNG, ROLE.ERT_CA, ROLE.ERT_DESIGN,
        ROLE.ERT_ANALYST])
    @swag_from('swagger_docs/user_get_list.yml')
    def get(self):
        """
        Get the list
        """

        user_read_schema = UserReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            user_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(User), operator)
            # making a copy of the main output schema
            user_schema = UserListSchema(
                exclude=UserListSchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                user_schema = UserListSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching users found')
            result = user_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class ChangePasswordAPI(AuthResource):
    """
    API for changing password
    """

    @swag_from('swagger_docs/user_change_password.yml')
    def put(self):
        """
        Change password
        """

        change_password_schema = ChangePasswordSchema()
        ret = ''
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            user = User.query.filter_by(email=g.current_user['email']).first()
            if user:
                data, errors = change_password_schema.load(json_data)
                if errors:
                    return errors, 422
                if user.check_password(data['old_password']):
                    user.set_password(data['new_password'])
                    user.token_key = generate_user_random_string()
                    db.session.add(user)
                    db.session.commit()
                    ret = 'Password successfully changed'
                    send_password_change_email.s(True, user.row_id).delay()
                else:
                    c_abort(404, message='Password does not match')
            else:
                c_abort(404, message='User does not match')
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': ret}, 200


class DesignLabChangePasswordAPI(AuthResource):
    """
    API for changing password
    """

    # @swag_from('swagger_docs/user_change_password.yml')
    def put(self):
        """
        Change password
        """

        change_password_schema = ChangePasswordSchema()
        ret = ''
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            user = User.query.filter_by(email=g.current_user['email']).first()
            if user:
                data, errors = change_password_schema.load(json_data)
                if errors:
                    return errors, 422
                if user.check_password(data['old_password']):
                    user.set_password(data['new_password'])
                    user.token_key = generate_user_random_string()
                    db.session.add(user)
                    db.session.commit()
                    ret = 'Password successfully changed'
                    designlab_send_password_change_email.s(
                        True, user.row_id).delay()
                else:
                    c_abort(404, message='Password does not match')
            else:
                c_abort(404, message='User does not match')
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': ret}, 200


class FirstTimeChangePasswordAPI(AuthResource):
    """
    API for first time change password
    """

    @swag_from('swagger_docs/user_first_time_change_password.yml')
    def put(self):
        """
        Change password and also change first password update flag
        """

        first_time_change_password_schema = FirstTimeChangePasswordSchema()
        ret = ''
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            user = User.query.filter_by(email=g.current_user['email']).first()
            if user and not user.f_password_updated:
                user.f_password_updated = True
                data, errors = first_time_change_password_schema.load(
                    json_data)
                if errors:
                    return errors, 422
                user.set_password(data['new_password'])
                user.token_key = generate_user_random_string()
                db.session.add(user)
                db.session.commit()
                ret = 'Password successfully changed'

            else:
                c_abort(404, message='User does not match')
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': ret}, 200


class UserOrderAPI(AuthResource):
    """
    PUT API for users ordering according to their sequence_id
    """

    @swag_from('swagger_docs/user_order_put.yml')
    def put(self):
        """
        update the user's sequence_id
        """
        user_order_schema = UserOrderSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input
            data, errors = user_order_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            row_ids = data['user_ids']
            count = 1

            # ordering the row_ids according to input for fetching the
            # users in the same order
            ordering = case(
                {row_id: index for index, row_id in enumerate(row_ids)},
                value=User.row_id)
            users = User.query.filter(
                User.row_id.in_(row_ids)).order_by(
                ordering).all()

            # update the user sequence_id for ordering
            for user in users:
                user.sequence_id = count
                count += 1
                db.session.add(user)
            db.session.commit()

        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Users Updated'}, 200


class AdminUserOrderAPI(AuthResource):
    """
    update API for users oredering
    """

    @role_permission_required(perms=[ROLE.EPT_NU], roles=[
        ROLE.ERT_SU, ROLE.ERT_MNG])
    @swag_from('swagger_docs/admin_user_order_put.yml')
    def put(self):
        """
        update the user's sequence_id
        """
        admin_user_order_schema = AdminUserOrderSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input
            data, errors =\
                admin_user_order_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            row_ids = data['user_ids']
            count = 1

            # ordering the row_ids according to input for fetching the
            # users in the same order
            ordering = case(
                {row_id: index for index, row_id in enumerate(row_ids)},
                value=User.row_id)
            users = User.query.filter(
                User.row_id.in_(row_ids)).order_by(
                ordering).all()

            # update the user sequence_id for ordering
            for user in users:
                user.sequence_id = count
                count += 1
                db.session.add(user)
            db.session.commit()

        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Users Updated'}, 200
