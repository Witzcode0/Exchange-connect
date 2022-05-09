"""
Helper classes/functions for "unsubscriptions" package.
"""

import urllib.parse
import base64

from flask import current_app

from app.common.utils import get_payload_from_value, get_value_from_payload
from app.resources.unsubscriptions.models import (
    Unsubscription, UnsubscribeReason)
from app.base import constants as APP
from app import db


def generate_unsubscribe_email_link(email,domain_id=None):
    """
    Function that generates the unsubscribe link.

    :param email:
        the email for which to generate the unsubscribe link
    :return url:
        returns the verify link.
    """
    url = None
    if email:
        # generate token
        payload = get_payload_from_value(email)
        if domain_id == 8:
            url = urllib.parse.urljoin(
                current_app.config['FRONTEND_UAE_DOMAIN'],
                current_app.config['UNSUBSCRIBE_PATH'])
        else:
            url = urllib.parse.urljoin(
                current_app.config['FRONTEND_DOMAIN'],
                current_app.config['UNSUBSCRIBE_PATH'])
        url += payload
        email = base64.b64encode(email.encode('utf-8')).decode('utf-8')
        url += '&email=' + email
    return url


def verify_unsubscribe_email_token(token):
    """
    Get the email value from token
    """

    email = None
    try:
        email = get_value_from_payload(token, max_age=5184000)
    except Exception as e:
        email = None
    return email


def is_unsubscription(email, event_type, model=None):
    is_unsubscribed = False
    unsub = Unsubscription.query.filter_by(email=email).first()
    if unsub and event_type in unsub.events:
        is_unsubscribed = True
        if model:
            model.email_status = APP.EMAIL_UNSUB
            db.session.add(model)
            db.session.commit()
    return is_unsubscribed


def create_default_unsubscription(email):
    """
    Create unsubscription by default when user created
    :param email: email id of user
    :return:
    """
    if not Unsubscription.query.filter(Unsubscription.email == email).first():
        reason = UnsubscribeReason.query.first()
        unsub = Unsubscription(
            email=email, reason_id=reason.row_id, events=[])
        db.session.add(unsub)
        db.session.commit()
    return
