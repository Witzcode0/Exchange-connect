"""
Helpers for contact requests
"""

from sqlalchemy import and_, or_

from app.resources.contact_requests.models import ContactRequest
from app.resources.contacts.models import Contact
from app.resources.contact_requests import constants as CONTACT


def check_contact_request_exists(data):
    """
    Check if a "sent" or "accepted" contact request already exists
    * can raise exceptions, so catch in calling methods

    :param data:
        contact request object
    :return:
        empty string in case of no errors, else error message string
    """

    # check db for contact request
    contact_request_data = ContactRequest.query.filter(and_(
        ContactRequest.sent_by == data.sent_by,
        ContactRequest.sent_to == data.sent_to)).first()

    if contact_request_data:
        if contact_request_data.status == CONTACT.CRT_SENT:
            return 'Contact request already sent'
        elif contact_request_data.status == CONTACT.CRT_ACCEPTED:
            return 'Contact already added'

    return ''


def check_contact_exists(data):
    """
    Check if Contact already exists for requested data
    * can raise exceptions, so catch in calling methods

    :param data:
        contact request object
    :return:
        empty string in case of no errors, else error message string
    """

    # check db for contact
    contact_data = Contact.query.filter(or_(and_(
        Contact.sent_by == data.sent_by,
        Contact.sent_to == data.sent_to),
        and_(Contact.sent_to == data.sent_by,
             Contact.sent_by == data.sent_to))).first()
    if contact_data:
        return 'Contact already added'

    return ''


def check_cross_contact_request(data):
    """
    Check that sendee has also sent a ContactRequest to sender,
    i.e. cross request

    :param data:
        contact request object
    :return:
        existing contact request object
    """

    # check db for existing request
    contact_request_data = ContactRequest.query.filter(and_(
        ContactRequest.sent_by == data.sent_to,
        ContactRequest.sent_to == data.sent_by,
        ContactRequest.status == CONTACT.CRT_SENT)).first()
    if contact_request_data:
        return contact_request_data

    return None
