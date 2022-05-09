"""
Helper classes/functions for "auth" package.
"""

import urllib.parse

from flask import current_app, render_template

from app.common.utils import send_email
from app.common.utils import get_payload_from_value, get_value_from_payload


def generate_password_reset_link(user, domain_config):
    """
    Function that generates the password reset link.

    :param user:
        a user model for which to generate reset link.
    :return url:
        returns the password reset link.
    """
    # generate token
    payload = get_payload_from_value(user.email)
    url = urllib.parse.urljoin(
        domain_config['FRONTEND_DOMAIN'],
        '/'.join([current_app.config['PASSWORD_RESET_PATH'], payload]))
    return url


def verify_password_reset_link(payload):
    """
    Function that generates the password reset link.

    :param payload:
        the payload passed in url
    :return email:
        returns decoded email, if verfied link, else returns None
    """
    # decode token
    try:
        email = get_value_from_payload(payload, max_age=86400)
    except Exception as e:
        email = None
    return email


def send_password_reset_link(user, link):
    """
    for sending reset password link to user email
    """
    try:
        to_addresses = [user.email]
        from_name = current_app.config['DEFAULT_SENDER_NAME']
        from_email = current_app.config['DEFAULT_SENDER_EMAIL']
        reply_to = ''
        subject = '%(brand_name)s – Reset password link'
        html = ''
        with open('email_html_docs/password_reset_template.html', 'r') \
                as htmlfile:
            html = htmlfile.read()
        attachment = ''
        subject = subject % {'brand_name': current_app.config['BRAND_NAME']}
        body = 'Hi %(user_name)s,\r\n\r\n' + \
            'We have just received a password reset request for %(email)s.' + \
            ' Click on the below link to reset your password: \r\n' +\
            link + '\r\n\r\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body_dict = {
            'user_name': user.profile.first_name,
            'email': user.email, 'link': link,
            'helpdesk_number': current_app.config['HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME']}
        body = body % body_dict
        html = html.format(**body_dict)
        # send user email
        if not current_app.config['DEBUG']:
            send_email(current_app.config['SMTP_USERNAME'],
                       current_app.config['SMTP_PASSWORD'],
                       current_app.config['SMTP_HOST'],
                       subject=subject, from_name=from_name,
                       from_email=from_email, to_addresses=to_addresses,
                       reply_to=reply_to, body=body, html=html,
                       attachment=attachment)
        return 'For your security, we need to verify your identity. ' +\
            'We have sent a password reset link to the email: %s' %\
            str(user.email), ''

    except Exception as e:
        current_app.logger.exception(e)
        return '', 'Unknown error occurred, please try again.'


def send_designlab_password_reset_link(user, link):
    """
    for sending reset password link to user email
    """
    try:
        to_addresses = [user.email]
        from_name = current_app.config['DEFAULT_SENDER_NAME']
        from_email = current_app.config['DEFAULT_SENDER_EMAIL']
        reply_to = ''
        subject = 'Team Design Lab'
        attachment = ''
        body = 'Hi %(user_name)s,\r\n\r\n' + \
            'We have just received a password reset request for %(email)s.' + \
            ' Click on the below link to reset your password: \r\n' +\
            link + '\r\n\r\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nWarm regards,\r\n' + \
                'Team Design Lab'
        body_dict = {
            'user_name': user.profile.first_name,
            'email': user.email, 'link': link,
            'helpdesk_number': current_app.config['HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME']}
        body = body % body_dict
        html = render_template(
            'designlab_password_reset_template.html', **body_dict)
        # send user email
        if not current_app.config['DEBUG']:
            send_email(current_app.config['SMTP_USERNAME'],
                       current_app.config['SMTP_PASSWORD'],
                       current_app.config['SMTP_HOST'],
                       subject=subject, from_name=from_name,
                       from_email=from_email, to_addresses=to_addresses,
                       reply_to=reply_to, body=body, html=html,
                       attachment=attachment)
        return 'For your security, we need to verify your identity. ' +\
            'We have sent a password reset link to the email: %s' %\
            str(user.email), ''

    except Exception as e:
        current_app.logger.exception(e)
        return '', 'Unknown error occurred, please try again.'
