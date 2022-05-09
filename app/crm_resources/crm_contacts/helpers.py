"""
Helper classes/functions for "crm contacts" package.
"""

import base64
import datetime

from flask import current_app, g
from sqlalchemy import and_

from app import db
from app.resources.users.models import User
from app.resources.users.helpers import generate_user_random_string
from app.resources.accounts import constants as ACCOUNT
from app.resources.accounts.models import Account
from app.resources.roles.models import Role
from app.resources.roles import constants as ROLE
from app.resources.guest_user.schemas import GuestUserSchema
from app.resources.user_profiles.schemas import UserProfileSchema
from app.crm_resources.crm_file_library.models import CRMLibraryFile
from app.resources.unsubscriptions.helpers import create_default_unsubscription
from app.resources.contact_requests.helpers import \
    check_contact_request_exists, check_contact_exists, \
    check_cross_contact_request
from app.resources.contacts.models import Contact
from app.resources.notifications import constants as NOTIFY
# from app.resources.contact_requests.schemas import (
#     ContactRequestSchema)
from app.resources.contact_requests.models import ContactRequest
from app.resources.contact_requests import constants as CONREQUEST
from app.resources.user_settings.helpers import create_default_user_settings
from app.domain_resources.domains.helpers import (
    get_domain_name, get_domain_info)


def add_user_for_contact(data):
    """
    Adding contact in user table as guest user
    """
    responce = {'user': None, 'is_system_user': False, 'extra_message': None,
                'contact_req': None, 'is_connected': False}
    # base dict
    user_data_dict = {}
    # profile dict
    user_profile_dict = {}
    try:
        role_id = Role.query.filter_by(name=ROLE.ERT_NO).first().row_id

        user_profile_dict['first_name'] = data.first_name
        user_profile_dict['last_name'] = data.last_name or " "
        user_profile_dict['phone_number'] = data.phone_number
        user_profile_dict['company'] = data.company
        user_profile_dict['designation'] = data.designation
        user_profile_dict['address_street_one'] = data.address_street_one
        user_profile_dict['address_street_two'] = data.address_street_two
        user_profile_dict['address_city'] = data.address_city
        user_profile_dict['address_state'] = data.address_state
        user_profile_dict['address_zip_code'] = data.address_zip_code
        user_profile_dict['address_country'] = data.address_country
        # user dict
        user_data_dict['email'] = data.email
        user_data_dict['password'] = base64.b64encode(
                    bytes(generate_user_random_string().encode('utf-8')))
        user_data_dict['role_id'] = role_id
        user_data_dict['profile'] = user_profile_dict
        user_data_dict['is_crm_contact'] = True
        user_data_dict['accepted_terms'] = True

        user_data = User.query.filter(User.email == data.email).first()

        if (user_data and user_data.account_type == ACCOUNT.ACCT_GUEST and
                user_data.is_crm_contact):
            # if changes any in contact so user and user profile data also
            # change
            data_profile, errors = UserProfileSchema().load(
                user_data_dict['profile'], instance=user_data.profile,
                partial=True)
            if errors:
                responce['extra_message'] = errors
                return responce
            user_data_dict.pop('profile')
            user, errors = GuestUserSchema().load(
                user_data_dict, instance=user_data, partial=True)
            if errors:
                responce['extra_message'] = errors
                return responce
            user.updated_by = 1
            db.session.add(user)
            db.session.commit()
            responce['user'] = user_data
        elif (user_data and user_data.account_type == ACCOUNT.ACCT_GUEST and
              not user_data.is_crm_contact):
            responce['user'] = user_data
        elif user_data and user_data.account_type != ACCOUNT.ACCT_GUEST:
            responce['user'] = user_data
            responce['is_system_user'] = True
            json_data = {"sent_by": g.current_user['row_id'],
                         "sent_to": user_data.row_id,
                         "status": CONREQUEST.CRT_SENT}
            contact_req= ContactRequest(**json_data)
            result = check_contact_exists(contact_req)
            if result:
                responce['is_connected'] = True
            else :
                result = check_cross_contact_request(contact_req)
                if result:
                    result.status = CONREQUEST.CRT_ACCEPTED
                    result.accepted_rejected_on = \
                        datetime.datetime.utcnow()

                    db.session.add(result)
                    contact = Contact(sent_by = contact_req.sent_by,
                                      sent_to = contact_req.sent_to)
                    db.session.add(contact)
                    db.session.commit()
                    responce['contact_req'] = {'row_id': result.row_id,
                        'noti_type': NOTIFY.NT_CONTACT_REQ_ACCEPTED,
                        'user_ids': [contact_req.sent_by, contact_req.sent_to]
                    }

                if not result:
                    result = check_contact_request_exists(contact_req)
                    if not result:
                        # no contact request exists with status sent or
                        # accepted
                        db.session.add(contact_req)
                        db.session.commit()
                        responce['contact_req'] = {
                            'row_id': contact_req.row_id,
                            'noti_type': NOTIFY.NT_CONTACT_REQ_RECEIVED}

            responce['extra_message'] = {
                'message': str(user_data.email) + ' is already system '
                'user, are you want to connection request for user', 'user_id':
                    user_data.row_id}
        else:
            user, errors = GuestUserSchema().load(user_data_dict)
            if errors:
                responce['extra_message'] = errors
                return responce
            if not user.account_id:
                domain_name = get_domain_name()
                domain_id, domain_config = get_domain_info(domain_name)
                account_data = Account.query.filter_by(
                    account_type=ACCOUNT.ACCT_GUEST,
                    domain_id=domain_id).first()
                user.account_type = account_data.account_type
                user.account_id = account_data.row_id
                user.profile.account_type = account_data.account_type
                user.profile.account_id = account_data.row_id
            user = create_default_user_settings(user)
            user.sequence_id = 1
            user.created_by = 1
            user.updated_by = 1
            db.session.add(user)
            db.session.commit()
            # create unsubscription for user
            create_default_unsubscription(user.email)
            responce['user'] = user
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(e)
        responce['user'] = False
        return responce

    return responce


def update_user_id_from_crm_file(old_user_id, new_user_id):
    """
    When email update so user relation will be change, so change old_user_id to
    new_user_id in crm library file for related with current_user conatct
    :return:
    """
    CRMLibraryFile.query.filter(and_(
        CRMLibraryFile.created_by == g.current_user['row_id'],
        CRMLibraryFile.user_id == old_user_id)).update({
            CRMLibraryFile.user_id: new_user_id}, synchronize_session=False)
    db.session.commit()

    return
