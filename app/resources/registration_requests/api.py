"""
API endpoints for "registration requests" package.
"""

import base64

import datetime

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy import any_, func
from sqlalchemy.orm import load_only
from flasgger.utils import swag_from

from app import db, c_abort, g
from app.base.api import AuthResource, BaseResource
from app.auth.decorators import role_permission_required
from app.resources.registration_requests import constants as REGREQUEST
from app.resources.registration_requests.models import RegistrationRequest
from app.resources.registration_requests.schemas import (
    RegistrationRequestSchema, RegistrationRequestReadArgsSchema,
    UserProfileCommonSchema)
from app.resources.registration_requests.helpers import (
    verify_verify_email_link, send_mail_rejected_user, create_user_json,
    link_new_user_to_invitee)
from app.resources.roles import constants as ROLE
from app.resources.users.schemas import UserSchema
from app.resources.user_profiles.schemas import UserProfileSchema
from app.resources.accounts.models import Account
from app.resources.accounts import constants as ACCOUNT
from app.resources.accounts.helpers import transfer_account_object
from app.base import constants as APP
from app.resources.users.models import User
from app.resources.user_settings.helpers import create_default_user_settings
# from app.resources.users.helpers import (
#    check_account_membership, check_role_allowed)
from app.resources.users.helpers import (
    check_users_exist_for_account, generate_user_random_string)
from app.resources.contacts.helpers import create_default_contacts
from app.resources.account_user_members.helpers import (
    add_user_member_for_child_accounts)
from app.resources.unsubscriptions.helpers import create_default_unsubscription
from app.domain_resources.domains.helpers import (
    get_domain_name, get_domain_info)

from queueapp.user_email_tasks import (
    send_verify_email_email, send_registration_request_email,
    send_user_welcome_email, send_invitation_verify_email_email)
from queueapp.accounts.account_stats_tasks import update_account_stats


class RegistrationRequestPostAPI(BaseResource):
    """
    For creating new registration requests
    """

    @swag_from('swagger_docs/registration_request_post.yml')
    def post(self):
        """
        Create a registration request
        """

        registration_schema = RegistrationRequestSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = registration_schema.load(json_data)
            print(data, errors)
            if errors:
                c_abort(422, errors=errors)

            if not data.accepted_terms:
                c_abort(422, message='Requested user not accepted terms')
            # no errors, so add data to db
            data.status = REGREQUEST.REQ_ST_PENDING
            domain_id, domain_config = get_domain_info(get_domain_name())
            data.domain_id = domain_id
            db.session.add(data)
            db.session.commit()
            # send registration request details
            send_registration_request_email.s(True, data.row_id).delay()
            # send user welcome mail
            send_user_welcome_email.s(True, data.row_id).delay()
            # send email for verifying request
            # #TODO: may be used in future
            # url = generate_verify_email_link(data)
            # message, errors = send_verify_email_email(data, url)
            # #TODO: act on errors
            # #TODO: send emails to admin
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
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'RegistrationRequest submitted: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201


class DesignLabRegistrationRequestPostAPI(BaseResource):
    """
    For creating new registration requests
    """

    @swag_from('swagger_docs/registration_request_post.yml')
    def post(self):
        """
        Create a registration request
        """

        registration_schema = RegistrationRequestSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = registration_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            if not data.accepted_terms:
                c_abort(422, message='Requested user not accepted terms')
            # no errors, so add data to db
            data.only_design_lab = True
            data.status = REGREQUEST.REQ_ST_PENDING
            domain_id, domain_config = get_domain_info(get_domain_name())
            data.domain_id = domain_id
            db.session.add(data)
            db.session.commit()
            # send registration request details
            send_registration_request_email.s(True, data.row_id).delay()
            # send user welcome mail
            send_user_welcome_email.s(True, data.row_id).delay()
            # send email for verifying request
            # #TODO: may be used in future
            # url = generate_verify_email_link(data)
            # message, errors = send_verify_email_email(data, url)
            # #TODO: act on errors
            # #TODO: send emails to admin
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
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'RegistrationRequest submitted: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201


class RegistrationRequestEmailVerifyAPI(BaseResource):
    """
    Verfiy the email of a registration request
    """

    @swag_from('swagger_docs/registration_request_verify.yml')
    def put(self, token):
        """
        Updates the registration request status on successful verification link

        :param token: verify email token
        """
        json_data = {}
        json_data = request.get_json()
        try:
            user = None
            email,error = verify_verify_email_link(token)
            if error:
                c_abort(422, errors=error)

            if email:
                user = User.query.filter_by(
                    email=email).first()

            if not user:
                return c_abort(404, message='Bad email')

            if not user.unverified:
                return {'message': 'Email already verified'}, 200

            # user data change only when registration request created by admin
            req_by_admin = RegistrationRequest.query.filter_by(
                email=email).first().by_admin
            if req_by_admin:
                # only limited data will be change by user
                if json_data:
                    if 'password' in json_data and json_data['password']:
                        json_data['password'] = base64.b64decode(
                            json_data['password']).decode('utf-8')
                        user.set_password(json_data['password'])
                    if 'first_name' in json_data and json_data['first_name']:
                        user.profile.first_name = json_data['first_name']
                    if 'last_name' in json_data and json_data['last_name']:
                        user.profile.last_name = json_data['last_name']
                    if 'phone_number' in json_data and json_data[
                            'phone_number']:
                        user.profile.phone_number = json_data[
                            'phone_number']
            # email is verified, update unverified to False
            user.unverified = False
            db.session.add(user)
            db.session.commit()
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Email has been successfully verified'}, 200

    def get(self, token):
        """
        Get registration data on successful verification link
        :param token:
        :return:
        """
        try:
            regreq_data = None
            email, error = verify_verify_email_link(token)
            if error:
                c_abort(422, errors=error)

            if email:
                regreq_data = RegistrationRequest.query.filter_by(
                    email=email).first()

            if not regreq_data:
                return c_abort(404, message='Bad email')

            if 'Origin' in request.headers:
                origin = request.headers['Origin'].strip().split(".")[1:]
                domain_name = ".".join(origin)
                if not domain_name == regreq_data.domain.name:
                    return c_abort(404, message="Bad Domain")

            result = RegistrationRequestSchema().dump(regreq_data)
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'results': result}, 200


class RegistrationRequestAPI(AuthResource):
    """
    API for managing registration requests
    """

    @role_permission_required(perms=[ROLE.EPT_NU])
    @swag_from('swagger_docs/registration_request_put.yml')
    def put(self, row_id):
        """
        Update a registration request
        """

        registration_schema = RegistrationRequestSchema()
        # first find model
        model = None
        try:
            model = RegistrationRequest.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='RegistrationRequest id: %s'
                        ' does not exist' % str(row_id))
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
            data, errors = registration_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()

            if data.status == REGREQUEST.REQ_ST_REJECTED:
                message, error = send_mail_rejected_user(data)

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
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Updated RegistrationRequest id: %s' %
                str(row_id)}, 200

    @role_permission_required(perms=[ROLE.EPT_NU])
    @swag_from('swagger_docs/registration_request_delete.yml')
    def delete(self, row_id):
        """
        Delete a registration request
        """

        model = None
        try:
            # first find model
            model = RegistrationRequest.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='RegistrationRequest id: %s'
                        ' does not exist' % str(row_id))
            # if model is found, and not yet deleted, delete it
            model.deleted = True
            db.session.add(model)
            db.session.commit()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204

    @role_permission_required(perms=[ROLE.EPT_NU])
    @swag_from('swagger_docs/registration_request_get.yml')
    def get(self, row_id):
        """
        Get a registration request by id
        """

        registration_schema = RegistrationRequestSchema()
        model = None
        try:
            # first find model
            model = RegistrationRequest.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='RegistrationRequest id: %s'
                        ' does not exist' % str(row_id))
            result = registration_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class RegistrationRequestReSendEmailVerifyAPI(AuthResource):
    """
    Resend the verification email of a registration request
    """

    @role_permission_required(perms=[ROLE.EPT_NU])
    @swag_from('swagger_docs/registration_request_resend_email_verify.yml')
    def put(self, row_id):
        """
        Resend the verification email
        """

        model = None
        reg_model = None
        message = 'Nothing to do'
        try:
            model = User.query.get(row_id)
            if model is None or model.deleted or not model.unverified:
                c_abort(404, message='User id: %s'
                                     ' does not exist' % str(row_id))
            reg_model = RegistrationRequest.query.filter_by(
                email=model.email).first()
            if not reg_model:
                c_abort(404, message='RegistrationRequest id: %s'
                                     ' does not exist' % str(row_id))

            if reg_model.status == REGREQUEST.REQ_ST_ACCEPTED:
                # send email
                if reg_model.by_admin:
                    send_invitation_verify_email_email.s(True, reg_model.row_id).delay()
                else:
                    send_verify_email_email.s(True, reg_model.row_id).delay()
                message = 'Verification email resent for request: %s' %\
                    str(row_id)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'message': message}, 200


class RegistrationRequestAddUserAPI(AuthResource):
    """
    API for adding a user from a registration request
    """

    @role_permission_required(perms=[ROLE.EPT_NU])
    @swag_from('swagger_docs/registration_request_adduser.yml')
    def put(self, row_id):
        """
        Add a user, and update registration request
        """
        user_schema = UserSchema()
        user_profile_schema = UserProfileSchema()
        user_common_schema = UserProfileCommonSchema()
        model = None
        user_model = None
        try:
            model = RegistrationRequest.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='RegistrationRequest id: %s'
                                     ' does not exist' % str(row_id))
            user_model = User.query.filter_by(email=model.email).first()
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
            if model.status != REGREQUEST.REQ_ST_PENDING:
                c_abort(422, message='Unverified user')

            # validate and deserialize input
            json_data, errors = user_common_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            if 'join_as' in json_data:
                json_data.pop('join_as')
            if 'password' not in json_data:
                # setup a basic password before actual auto generation
                json_data['password'] = base64.b64encode(
                        bytes(generate_user_random_string().encode('utf-8')))

            # for user data
            user_data = create_user_json(json_data)
            user_profile_data = None
            updated_account_id = False
            # requested user already exists with guest user
            if user_model and user_model.account_type == ACCOUNT.ACCT_GUEST:
                user_profile_data, errors = user_profile_schema.load(
                    user_data['profile'], instance=user_model.profile,
                    partial=True)
                if errors:
                    return c_abort(422, errors=errors)

                user_data.pop('profile')
                user_final_data, errors = user_schema.load(
                    user_data, instance=user_model, partial=True)
                if errors:
                    return c_abort(422, errors=errors)
                updated_account_id = True
            else:
                user_final_data, errors = user_schema.load(user_data)
                if errors:
                    return c_abort(422, errors=errors)

            account_data = Account.query.filter(
                Account.row_id == user_final_data.account_id).options(
                load_only('account_type')).first()
            # no errors, so add data to db
            user_final_data.password = model.password
            user_final_data.created_by = g.current_user['row_id']
            user_final_data.updated_by = user_final_data.created_by
            user_final_data.account_type = account_data.account_type
            user_final_data.unverified = True
            user_final_data.only_design_lab = model.only_design_lab

            user_final_data.profile.account_type = account_data.account_type
            user_final_data.profile.account_id = user_final_data.account_id
            user_final_data.token_key = generate_user_random_string()
            model.status = REGREQUEST.REQ_ST_ACCEPTED

            user_final_data = create_default_user_settings(user_final_data)
            # add account activation date
            account = Account.query.filter_by(
                row_id=user_final_data.account_id).first()
            if not check_users_exist_for_account(user_final_data.account_id):
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
            if errors:
                c_abort(422, errors=errors)
            # fetch the users associated with the account
            # and get the highest in order sequence_id
            last_in_order_user = User.query.filter_by(
                account_id=user_final_data.account_id).order_by(
                User.sequence_id.desc()).first()
            if last_in_order_user:
                last_in_order_sequence_id = last_in_order_user.sequence_id
                # assign the sequence_id as new highest in order sequence_id
                user_final_data.sequence_id = last_in_order_sequence_id + 1
            else:
                user_final_data.sequence_id = 1
            db.session.add(model)
            db.session.add(user_final_data)
            db.session.commit()
            if account.account_type == ACCOUNT.ACCT_CORP_GROUP:
                add_user_member_for_child_accounts(
                    user_final_data.row_id, user_final_data.account_id,
                    user_final_data.is_admin)
            # send verification email
            send_verify_email_email.s(True, model.row_id).delay()
            # for account stats update
            update_account_stats.s(True, user_final_data.account_id).delay()
            # add default contacts
            create_default_contacts(user_final_data.row_id)
            # create default unsubsription
            create_default_unsubscription(user_final_data.email)
            # check if user is already there in any event
            link_new_user_to_invitee(user_final_data.row_id,
                                     user_final_data.email)
            if updated_account_id:
                transfer_account_object(
                    user_final_data.row_id, user_final_data.account_id)
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
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'New user added id: %s' %
                           str(user_final_data.row_id)}, 200


class RegistrationRequestList(AuthResource):
    """
    Read API for registration request lists, i.e, more than
    1 registration request
    """

    model_class = RegistrationRequest

    def __init__(self, *args, **kwargs):
        super(RegistrationRequestList, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """

        status = None
        if 'status' in filters:
            status = filters.pop('status')
        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)
        # build specific extra queries filters
        full_name = ""
        if extra_query:
            if "full_name" in extra_query and extra_query['full_name']:
                full_name = '%' + (extra_query["full_name"]).lower() + '%'
                query_filters['filters'].append((func.concat(
                    func.lower(RegistrationRequest.first_name),
                    ' ',
                    func.lower(RegistrationRequest.last_name)).like(
                        full_name)))
        # for search multiple status
        if status:
            query_filters['filters'].append(
                RegistrationRequest.status == any_(status))

        query = self._build_final_query(
            query_filters, query_session, operator)
        return query, db_projection, s_projection, order, paging

    @role_permission_required(perms=[ROLE.EPT_NU])
    @swag_from('swagger_docs/registration_request_get_list.yml')
    def get(self):
        """
        Get the list
        """

        registration_read_schema = RegistrationRequestReadArgsSchema(
            strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            registration_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(RegistrationRequest),
                                 operator)
            # making a copy of the main output schema
            registration_schema = RegistrationRequestSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                registration_schema = RegistrationRequestSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching Registration Requests found')
            result = registration_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
