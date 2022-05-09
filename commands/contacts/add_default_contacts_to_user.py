import datetime

from flask_script import Command, Option
from flask import current_app
from sqlalchemy import and_, or_

from app import db
from app.resources.users.models import User
from app.resources.contact_requests.models import ContactRequest
from app.resources.contacts.models import Contact


class AddDefaultContactsToUser(Command):
    """
    Command to add default contacts to existing users
    """
    option_list = [
        Option('--verbose', '-v', dest='verbose', action='store_true',
               default=False),
        Option('--dry', '-dry', dest='dry', action='store_true',
               default=False),
    ]

    def run(self, verbose, dry):
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('Adding default contacts to existing user ...')
        try:
            usrs = User.query.order_by(User.row_id).all()
            # fetch the user list who should be
            # default contacts for each user
            sendee_list = current_app.config['DEFAULT_CONTACT_LIST']
            # check if user exists
            sendee_users = User.query.filter(User.row_id.in_(
                sendee_list)).all()
            for usr in usrs:
                for sendee_user in sendee_users:
                    try:
                        # if sendee and sender are same, dont create contact
                        if sendee_user.row_id == usr.row_id:
                            continue

                        # check db if user are already contacts
                        contact_data = Contact.query.filter(or_(and_(
                            Contact.sent_by == usr.row_id,
                            Contact.sent_to == sendee_user.row_id),
                            and_(Contact.sent_to == usr.row_id,
                                 Contact.sent_by == sendee_user.row_id
                                 ))).first()
                        if contact_data:
                            continue

                        # check if contact_request is already sent
                        contact_request_data = ContactRequest.query.filter(or_(
                            and_(ContactRequest.sent_by == usr.row_id,
                                 ContactRequest.sent_to == sendee_user.row_id),
                            and_(ContactRequest.sent_to == usr.row_id,
                                 ContactRequest.sent_by == sendee_user.row_id
                                 ))).first()
                        if contact_request_data:
                            # if contact request is already sent,
                            # then update status to accepted and create contact
                            contact_request_data.status = 'accepted'
                            db.session.add(contact_request_data)
                            # add the contact data to db
                            db.session.add(Contact(
                                sent_by=usr.row_id,
                                sent_to=sendee_user.row_id))
                            db.session.commit()
                            continue

                        # create new contact request and contacts
                        db.session.add(ContactRequest(
                            sent_by=usr.row_id, sent_to=sendee_user.row_id,
                            status='accepted'))
                        # add the contact data to db
                        db.session.add(Contact(
                            sent_by=usr.row_id,
                            sent_to=sendee_user.row_id))
                        db.session.commit()

                    except Exception as e:
                        db.session.rollback()
                        current_app.logger.exception(e)
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
