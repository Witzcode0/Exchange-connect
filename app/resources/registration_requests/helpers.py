"""
Helper classes/functions for "registration request" package.
"""

import urllib.parse

from flask import current_app
from itsdangerous import SignatureExpired

from app import db
from app.common.utils import (
    send_email, get_payload_from_value, get_value_from_payload)
# from app.webinar_resources.webinar_invitees.models import WebinarInvitee
from app.webcast_resources.webcast_invitees.models import WebcastInvitee
from app.corporate_access_resources.corporate_access_event_invitees.models \
    import CorporateAccessEventInvitee
from app.domain_resources.domains.helpers import (
    get_domain_info, get_domain_name)


def generate_verify_email_link(reg_req):
    """
    Function that generates the verify link.

    :param reg_req:
        a registration request model for which to generate verify link.
    :return url:
        returns the verify link.
    """

    sub_path = ''
    if reg_req.by_admin:
        sub_path = current_app.config['DIRECT_EMAIL_VERIFY_PATH']
    else:
        sub_path = current_app.config['EMAIL_VERIFY_PATH']
    # generate token
    payload = get_payload_from_value(reg_req.email)
    # design lab registration will not have domain
    domain_name = reg_req.domain.name if reg_req.domain \
        else get_domain_name(code="IN")
    domain_id, domain_config = get_domain_info(domain_name)
    current_app.logger.exception('987654321' + domain_config['FRONTEND_DOMAIN'])
    url = urllib.parse.urljoin(
        domain_config['FRONTEND_DOMAIN'],
        '/'.join([sub_path, payload]))
    return url


def verify_verify_email_link(payload):
    """
    Function that verifies the verify email link

    :param payload:
        the payload passed in url
    :return email:
        returns decoded email, if verified link, else returns None
    """

    # decode token
    email = None
    error = None
    try:
        email = get_value_from_payload(payload, max_age=86400)
    except SignatureExpired as e:
        error = 'link expired.'
    except Exception as e:
        email = None
    return email, error


def send_mail_generated_password(reg_req, first_name, generated_password):

    # #TODO: may be used in future, update it before re-enabling
    """
    Send email with generated password when admin accepts the registration
    request

    :param reg_req:
        registration request model object
    :param generated_password:
        generated password
    :param first_name:
        user first name
    :return:
        message, error tuple
    """

    try:
        to_addresses = [reg_req.email]
        from_name = current_app.config['DEFAULT_SENDER_NAME']
        from_email = current_app.config['DEFAULT_SENDER_EMAIL']
        reply_to = ''
        subject = 'Corporate Solution User Registration'
        html = ''
        attachment = ''

        body = 'Hi %(user_name)s,\r\n\r\n' + \
               'The administrator has accepted you as a user' + \
               ' and you have issued with a temporary password.' + \
               '\r\n'
        body += 'Your current login information is now: ' + \
                '\n\t\tEmail:"%(user_email)s"\n ' + \
                '\t\tPassword:"%(password)s"'
        body += '\n\n( You will have to change your password' + \
                ' when you login for the first time. )'
        replace_dict = {'user_name': first_name.capitalize(),
                        'user_email': reg_req.email,
                        'password': generated_password}
        body = body % replace_dict
        # send user email
        if not current_app.config['DEBUG']:
            send_email(current_app.config['SMTP_USERNAME'],
                       current_app.config['SMTP_PASSWORD'],
                       current_app.config['SMTP_HOST'],
                       subject=subject, from_name=from_name,
                       from_email=from_email, to_addresses=to_addresses,
                       reply_to=reply_to, body=body, html=html,
                       attachment=attachment)
            return 'We need to verify your identity and email in order to ' + \
                   'proceed with your registration. ' + \
                   'We have sent an email verification link to the email: ' +\
                   '%s' % str(reg_req.email), ''
    except Exception as e:
        current_app.logger.exception(e)
        return '', 'Unknown error occurred, please try again.'

    return '', ''


def send_mail_rejected_user(reg_req):
    """
    send mail to rejected user by admin
    :param reg_req: registration request model object
    :return:
    """

    try:
        to_addresses = [reg_req.email]
        from_name = current_app.config['DEFAULT_SENDER_NAME']
        from_email = current_app.config['DEFAULT_SENDER_EMAIL']
        reply_to = ''
        subject = 'Corporate Solution User Registration'
        html = ''
        attachment = ''
        with open('email_html_docs/registration_requests/'
                  'registration_request_rejected.html', 'r') as htmlfile:
            html = htmlfile.read()
        body = 'Hi %(user_name)s,\r\n\r\n' + \
               'Hope you are doing well. We regret to inform that your' \
               ' registration request for Corporate Solution user' \
               ' has been rejected. ' + \
               '\r\n'
        replace_dict = {'user_name': reg_req.first_name.capitalize()}
        body = body % replace_dict
        html = html.format(**replace_dict)
        # send user email
        if not current_app.config['DEBUG']:
            send_email(current_app.config['SMTP_USERNAME'],
                       current_app.config['SMTP_PASSWORD'],
                       current_app.config['SMTP_HOST'],
                       subject=subject, from_name=from_name,
                       from_email=from_email, to_addresses=to_addresses,
                       reply_to=reply_to, body=body, html=html,
                       attachment=attachment)
            return 'We need to verify your identity and email in order to ' + \
                   'proceed with your registration. ' + \
                   'We have sent an email verification link to the email: ' +\
                   '%s' % str(reg_req.email), ''
    except Exception as e:
        current_app.logger.exception(e)
        return '', 'Unknown error occurred, please try again.'


def create_user_json(json_data):
    """
    Collects required data for user and user profile from json_data and returns
    a dictionary in the expected format for creation of user, and user profile
    using "UserSchema".

    :param json_data:
        the validated json_data from the request
    :return: dictionary in expected format for use in UserSchema
    """

    # base dict
    user_data_dict = {}
    # profile dict
    user_profile_dict = {}
    user_profile_dict['first_name'] = json_data['first_name']
    user_profile_dict['last_name'] = json_data['last_name']
    user_profile_dict['company'] = json_data['company']
    user_profile_dict['phone_number'] = json_data['phone_number']
    user_profile_dict['designation'] = json_data['designation']
    # user dict
    user_data_dict['email'] = json_data['email']
    user_data_dict['password'] = json_data['password']
    user_data_dict['role_id'] = json_data['role_id']
    user_data_dict['account_id'] = json_data['account_id']
    if 'is_admin' in json_data:
        user_data_dict['is_admin'] = json_data['is_admin']
    user_data_dict['profile'] = user_profile_dict
    user_data_dict['accepted_terms'] = 'True'

    return user_data_dict


def link_new_user_to_invitee(row_id, email):
    """
    Check if user is already invited in any of the events then add
    user id to that respective event
    """

    try:
        # check and update caevent invitees
        CorporateAccessEventInvitee.query.filter(
            CorporateAccessEventInvitee.invitee_email == email,
            CorporateAccessEventInvitee.user_id.is_(None)).update(
            {"user_id": row_id})
        db.session.commit()

        # check webcast
        webcast_event = WebcastInvitee.query.filter(
            WebcastInvitee.invitee_email == email,
            WebcastInvitee.user_id.is_(None)).all()
        if webcast_event:
            for invitee in webcast_event:
                invitee.user_id = row_id
                db.session.add(invitee)
                db.session.commit()
        """
        # check webinar
        webinar_event = WebinarInvitee.query.filter_by(
            WebinarInvitee.invitee_email == email,
            WebinarInvitee.user_id.is_(None)).all()
        if webinar_event:
            for invitee in webinar_event:
                invitee.user_id = row_id
                db.session.add(invitee)
                db.session.commit()"""
    except Exception as e:
        current_app.logger.exception(e)
        return '', 'Unknown error occurred, please try again.'
