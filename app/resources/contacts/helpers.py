"""
Helpers for contacts
"""
from flask import current_app
from app import db

from app.resources.contact_requests.models import ContactRequest
from app.resources.contacts.models import Contact
from app.resources.users.models import User


def create_default_contacts(sender):
    """
    creating default contact while creating a new user
    :param helper:
        new user getting created
    """

    # fetch the user list who should be default contacts for each user
    sendee_list = current_app.config['DEFAULT_CONTACT_LIST']
    try:
        # check if user exists
        sendee_users = User.query.filter(User.row_id.in_(sendee_list)).all()
        for sendee_user in sendee_users:
            try:
                # send contact-requests to default contacts
                db.session.add(ContactRequest(
                    sent_by=sender, sent_to=sendee_user.row_id,
                    status='accepted'))
                # add the contact data to db
                db.session.add(Contact(
                    sent_by=sender, sent_to=sendee_user.row_id))
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                current_app.logger.exception(e)
    except Exception as e:
        raise e
    return
