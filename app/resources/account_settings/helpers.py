"""
Helper classes/functions for "account settings" package.
"""

from flask import current_app

from app.common.utils import (
    verify_ses_sender_identity, check_ses_identity_verification_status,
    check_domain_records, remove_ses_identity)


def send_verification_email(email_address):
    """
    Send the verification email with vendor api

    :returns a dictionary with 'status' and 'response', indicating status of
        email sent, and response from vendor api
    """

    response = {'status': False, 'response': {}}

    try:
        response['status'], response['response'] = verify_ses_sender_identity(
            email_address, custom_template_name=current_app.config[
                'SES_CUSTOM_TEMPLATE'])
    except Exception as e:
        current_app.logger.exception(e)
        response['status'] = False

    return response


def check_identity_verified_status(identity):
    """
    Checks the domain/email address verification status with vendor api

    :returns a dictionary with 'status' and 'response', indicating status of
        verification, and response from vendor api
    """
    response = {'status': False, 'response': {}}

    try:
        response['status'], response['response'] =\
            check_ses_identity_verification_status(identity)
    except Exception as e:
        current_app.logger.exception(e)
        response['status'] = False

    return response


def check_domain_verified_status(identity):
    """
    Checks the domain DKIM/SPF records
    """

    result = False
    domain = identity
    if '@' in identity:
        domain = identity.split('@')[1]

    result, response = check_domain_records(domain)

    return result


def remove_verified_identity(identity):
    """
    Checks the domain/email address verification status with vendor api

    :returns a dictionary with 'status' and 'response', indicating status of
        verification, and response from vendor api
    """
    response = {'status': False, 'response': {}}

    try:
        response['status'], response['response'] = remove_ses_identity(
            identity)
    except Exception as e:
        current_app.logger.exception(e)
        response['status'] = False

    return response


def verify_email(account_settings, reverify=False, update_model=True):
    """
    Verifies if the sender email can be used for sending the email by verifying
    with SES, and DNS. Saves/updates the response by default, also updates the
    passed account settings model.

    :param account_settings:
        the account settings object
    :param reverify:
        boolean, indicating if the email should be reverified irrespective of
        current status
    :param update_model:
        boolean, indicating whether the model should be updated

    :returns a dictionary with 'result', 'extra_message' and 'account_settings'
        object indicating status of verification, any extra message (incase of
        errors), and account_settings object that was passed with modifications
        result can be either True (all verified),
        False (not verified or error), or None (verification email sent)
    """

    return_dict = {
        'result': False,
        'extra_message': '',
        'account_settings': account_settings
    }

    if not account_settings.event_sender_email:
        raise Exception('Event sender email not yet set')

    # first check if already verified and reverify is False
    if account_settings.verfied_status and not reverify:
        return_dict['result'] = True
        return return_dict

    # check if identity is verified on SES
    response = check_identity_verified_status(
        account_settings.event_sender_email)
    if response['status']:
        # if verified
        # check domain verified status
        result = check_domain_verified_status(
            account_settings.event_sender_email)
        if not result:
            return_dict['extra_message'] = 'Add some details for domain ' +\
                'verification.'
        if update_model:
            # update the account_settings model
            account_settings.event_sender_verified = response['status']
            account_settings.event_sender_domain_verified = result
            account_settings.ses_email_verification_status_response = response[
                'response']
            account_settings.load_verified_status()
        return_dict['result'] = result
        return_dict['account_settings'] = account_settings
    else:
        # identity not verified, send/resend email
        response = send_verification_email(account_settings.event_sender_email)
        if update_model:
            account_settings.event_sender_verified = False
            account_settings.event_sender_domain_verified = False
            account_settings.ses_email_verification_response = response[
                'response']
            account_settings.load_verified_status()
        if response['status']:
            # if sent
            # special None case, indicating domain verification is pending,
            # but verification email is sent
            return_dict['result'] = None
            return_dict['extra_message'] = 'Add some details for domain ' +\
                'verification.'
        else:
            return_dict['extra_message'] = 'Verification email could not be' +\
                ' sent, please try again in sometime.'

    return return_dict
