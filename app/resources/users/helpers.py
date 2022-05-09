"""
Helper classes/functions for "users" package.
"""

import string
import random

from flask import g, current_app
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from flask_restful import abort

from app import db, c_abort
from app.base import constants as APP
from app.resources.roles import constants as ROLE
from app.resources.roles.models import Role
from app.resources.users.models import User
from app.resources.registration_requests.models import RegistrationRequest
from app.resources.registration_requests import constants as REGREQ

from queueapp.user_email_tasks import send_invitation_verify_email_email


def check_account_membership(new_data, org_data=None):
    """
    Checks the account membership, and role of super admin, admin, manager
    """

    cuser = g.current_user
    if new_data.account_id != cuser['account_id']:
        if cuser['role']['name'] not in [
                ROLE.ERT_SU, ROLE.ERT_AD, ROLE.ERT_MNG]:
            return False

    return True


def check_role_allowed(new_data):
    """
    Checks if the role is allowed for this user
    """

    cuser = g.current_user
    if cuser['role']['name'] not in [ROLE.ERT_SU, ROLE.ERT_AD, ROLE.ERT_MNG]:
        not_allowed_roles = Role.query.filter(or_(
            Role.name == ROLE.ERT_SU, Role.name == ROLE.ERT_AD,
            Role.name == ROLE.ERT_MNG)).all()
        selected_role = Role.query.get(new_data.role_id)
        if selected_role in not_allowed_roles:
            return False

    return True


def check_users_exist_for_account(account_id):
    """
    Checks for account active or not(if particular account_id
    used for any user then it is active, if not then inactive)
    """
    user_data = User.query.filter_by(account_id=account_id).first()
    if user_data:
        return True
    return False


def add_registration_request_for_user(user_data, domain_id):
    """
    Add registration request entry for user which is created by admin
    :param user_data: object of user data
    :param domain_id: domain id
    :return:
    """
    json_data = {}
    try:
        if user_data:
            reg_req = RegistrationRequest(
                    email=user_data.email, password=user_data.password,
                    first_name=user_data.profile.first_name,
                    last_name=user_data.profile.last_name,
                    company=user_data.account.account_name,
                    designation=user_data.profile.designation,
                    phone_number=user_data.profile.phone_number,
                    join_as=user_data.account_type,
                    status=REGREQ.REQ_ST_ACCEPTED,
                    updated_by=user_data.created_by,
                    domain_id=domain_id,
                    by_admin=True)

            db.session.add(reg_req)
            db.session.commit()

            current_app.logger.exception("-" * 50)
            send_invitation_verify_email_email.s(True, reg_req.row_id).delay()
    except IntegrityError as e:
        db.session.rollback()
        if user_data:
            User.query.filter_by(row_id=user_data.row_id).delete(
                synchronize_session=False)
        if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
            # format of the message:
            # Key (email)=(example@example.com) already exists.
            column = e.orig.diag.message_detail.split('(')[1][:-2]
            c_abort(422, message=APP.MSG_ALREADY_EXISTS +
                    ' in registration request', errors={
                        column: [APP.MSG_ALREADY_EXISTS]})
        # for any other unknown db errors
        current_app.logger.exception(e)
        abort(500)
    return


def generate_user_random_string(size=2):
    """
    When password change then random value will be generate for validation
    :param size: size of random string
    :return: random generated key
    """
    lower_str = 'abcdefghijklmnopqrstuvwxyz'
    upper_str = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    special_str = '@$#!%*?&'
    digit_str = '0123456789'

    chars = ''.join(
        random.choice(lower_str) + random.choice(upper_str) +
        random.choice(special_str) + random.choice(digit_str)
        for _ in range(size))
    return chars


def include_current_users_groups_only():
    # overriding relationship for including current users groups only
    if hasattr(g, 'current_user'):
        User.crm_contact_grouped = db.relationship(
            'CRMGroup', secondary='groupcontacts',
            primaryjoin='groupcontacts.c.contact_id==User.row_id',
            secondaryjoin='and_('
                'groupcontacts.c.crm_group_id==CRMGroup.row_id,'
                'CRMGroup.created_by=='+str(g.current_user["row_id"])+')',
            viewonly=True)
