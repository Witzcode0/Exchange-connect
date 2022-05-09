import datetime

from flask_script import Command, Option
from sqlalchemy.orm import load_only
from sqlalchemy import or_

from app import db, c_abort
from app.resources.accounts.models import Account
from app.resources.account_profiles.models import AccountProfile
from app.resources.users.models import User
from app.resources.user_profiles.models import UserProfile
from app.resources.companies.models import Company
from app.resources.follows.models import CFollow, CFollowHistory
from app.resources.users import constants as USER
from app.resources.notifications import constants as NOTIFY
from app.common.helpers import delete_conference

from queueapp.user_stats_tasks import manage_users_stats
from queueapp.webinars.email_tasks import send_webinar_cancellation_email
from queueapp.webinars.notification_tasks import (
    add_webinar_cancelled_invitee_notification)
from queueapp.webcasts.email_tasks import send_webcast_cancelled_email
from queueapp.webcasts.notification_tasks import (
    add_webcast_cancelled_invitee_notification)
from queueapp.corporate_accesses.email_tasks import (
    send_corporate_access_event_cancellation_email)
from queueapp.corporate_accesses.notification_tasks import (
    add_cae_cancelled_invitee_notification)
from queueapp.ca_open_meetings.notification_tasks import (
    add_caom_cancelled_notification)

from app.webinar_resources.webinars.models import Webinar
from app.webcast_resources.webcasts.models import Webcast
from app.corporate_access_resources.corporate_access_events.models import (
    CorporateAccessEvent)
from app.corporate_access_resources.ca_open_meetings.models import (
    CAOpenMeeting)
from app.resources.corporate_announcements.models import CorporateAnnouncement
from app.resources.contacts.models import Contact
from app.resources.contacts.schemas import ContactHistorySchema
from app.resources.contact_requests.models import ContactRequest
from app.resources.contact_requests.schemas import ContactRequestHistorySchema


class DeleteUpdateAccounts(Command):
    """
    Command to delete or change accounts
    :arg verbose:
        print progress
    :arg dry:
        dry run
    """

    option_list = [
        Option('--verbose', '-v', dest='verbose', action='store_true',
               default=False),
        Option('--dry', '-dry', dest='dry', action='store_true',
               default=False),
        Option('--ids', '-i', dest='ids', default=None),
        Option('--source_ac_type', '-st', dest='stype', default=None),
        Option('--dest_ac_type', '-dt', dest='dtype', default=None),
        Option('--action', '-a', dest='action', required=True,
               choices=["delete", "change_ac_type"]),

    ]

    def run(self, verbose, dry, action, ids, stype, dtype):
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')

        try:
            if action == 'change_ac_type' and not dtype:
                print("provide destination account type")
                exit(0)

            if (not ids and not stype) or (ids and stype):
                print("provide either ids or account_type")
                exit(0)

            if ids:
                ids = [int(i) for i in ids.split(',')]

            update_clause = {'account_type': dtype}
            msg = 'changed account type of'
            tables = [Account, AccountProfile, User, UserProfile]
            del_user_ids = []
            if action == 'delete':
                update_clause = {'deleted': True}
                msg = 'deleted'
                if not ids:
                    tables.append(Company)

            for table in tables:
                tfilter = table.account_type.in_([stype])
                if ids:
                    tfilter = table.row_id.in_(ids)
                    if hasattr(table, 'account_id'):
                        tfilter = table.account_id.in_(ids)

                if table is Company:
                    models = table.query.filter(tfilter).delete(
                        synchronize_session=False)
                    print("{} {} {}".format(msg, models, table.__tablename__))
                    continue

                if (table is Account and action == 'change_ac_type'
                        and stype == 'sme'):
                    update_clause['is_sme'] = True

                if table is User and action == 'delete':
                    users = User.query.filter(
                        tfilter, User.deleted.is_(False)).options(
                        load_only('row_id'))
                    del_user_ids = [user.row_id for user in list(users)]

                models = table.query.filter(tfilter).update(
                    update_clause, synchronize_session=False)
                print("{} {} {}".format(msg, models, table.__tablename__))
                update_clause.pop('is_sme', None)

            if action == 'delete':
                # delete follow which following particular account
                if not ids:
                    accounts = Account.query.filter(
                        Account.account_type == stype).options(
                        load_only('row_id'))
                    ids = [account.row_id for account in accounts]
                count = 0
                batch_size = 100
                cfollow_data = CFollow.query.filter(
                    CFollow.company_id.in_(ids)).options(
                    load_only('sent_by', 'company_id'))

                for cfollow in list(cfollow_data):
                    count += 1
                    db.session.add(CFollowHistory(
                        sent_by=cfollow.sent_by,
                        company_id=cfollow.company_id))
                    if count >= batch_size:
                        db.session.commit()
                        count = 0
                    # update user total_companies
                    manage_users_stats.s(
                        True, cfollow.sent_by, USER.USR_COMPS,
                        increase=False).delay()
                CFollow.query.filter(CFollow.company_id.in_(ids)).delete(
                    synchronize_session=False
                )
                db.session.commit()

                # cancel all webinars which are upcoming and delete all drafts
                Webinar.query.filter(
                    Webinar.account_id.in_(ids),
                    Webinar.is_draft.is_(True)).delete(
                    synchronize_session=False
                )
                db.session.commit()
                upcoming_webinars = Webinar.query.filter(
                    Webinar.account_id.in_(ids),
                    Webinar.cancelled.is_(False),
                    Webinar.ended_at > datetime.datetime.utcnow())
                for webinar in upcoming_webinars:
                    count += 1
                    if webinar.conference_id:
                        delete_conference(data=webinar)

                    webinar.cancelled = True
                    db.session.add(webinar)
                    if count >= batch_size:
                        db.session.commit()
                        count = 0
                    send_webinar_cancellation_email.s(
                        True, webinar.row_id).delay()
                    # send webinar cancel notification to invitee
                    add_webinar_cancelled_invitee_notification.s(
                        True, webinar.row_id,
                        NOTIFY.NT_WEBINAR_CANCELLED).delay()

                print('webinars deleted')
                # cancel all webcasts which are upcoming and delete all drafts
                Webcast.query.filter(
                    Webcast.account_id.in_(ids),
                    Webcast.is_draft.is_(True)).delete(
                    synchronize_session=False)
                db.session.commit()
                upcoming_webcasts = Webcast.query.filter(
                    Webcast.account_id.in_(ids),
                    Webcast.cancelled.is_(False),
                    Webcast.ended_at > datetime.datetime.utcnow())
                for webcast in upcoming_webcasts:
                    count += 1
                    if webcast.conference_id:
                        delete_conference(data=webcast)

                    webcast.cancelled = True
                    db.session.add(webcast)
                    if count >= batch_size:
                        db.session.commit()
                        count = 0
                    send_webcast_cancelled_email.s(
                        True, webcast.row_id).delay()
                    # send webcast cancel notification to invitee
                    add_webcast_cancelled_invitee_notification.s(
                        True, webcast.row_id,
                        NOTIFY.NT_WEBCAST_CANCELLED).delay()

                print('webcasts deleted')
                # cancel all caevents which are upcoming and delete all drafts
                CorporateAccessEvent.query.filter(
                    CorporateAccessEvent.account_id.in_(ids),
                    CorporateAccessEvent.is_draft.is_(True)).delete(
                    synchronize_session=False
                )
                db.session.commit()
                upcoming_caevents = CorporateAccessEvent.query.filter(
                    CorporateAccessEvent.account_id.in_(ids),
                    CorporateAccessEvent.cancelled.is_(False),
                    CorporateAccessEvent.ended_at > datetime.datetime.utcnow())
                for caevent in upcoming_caevents:
                    count += 1

                    caevent.cancelled = True
                    db.session.add(caevent)
                    if count >= batch_size:
                        db.session.commit()
                        count = 0
                    send_corporate_access_event_cancellation_email.s(
                        True, caevent.row_id).delay()
                    # send caevent cancel notification to invitee
                    add_cae_cancelled_invitee_notification.s(
                        True, caevent.row_id,
                        NOTIFY.NT_WEBCAST_CANCELLED).delay()

                print('ca events deleted')
                # cancel all cao_meetings which are upcoming and delete all
                # drafts
                CAOpenMeeting.query.filter(
                    CAOpenMeeting.account_id.in_(ids),
                    CAOpenMeeting.is_draft.is_(True)).delete(
                    synchronize_session=False
                )
                db.session.commit()
                upcoming_cao_meetings = CAOpenMeeting.query.filter(
                    CAOpenMeeting.account_id.in_(ids),
                    CAOpenMeeting.cancelled.is_(False),
                    CAOpenMeeting.ended_at > datetime.datetime.utcnow())
                for cao_meeting in upcoming_cao_meetings:
                    count += 1
                    cao_meeting.cancelled = True
                    db.session.add(cao_meeting)
                    if count >= batch_size:
                        db.session.commit()
                        count = 0

                    # send notifications to slot inquiry confirmed users
                    add_caom_cancelled_notification.s(
                        True, cao_meeting.row_id,
                        NOTIFY.NT_CAOM_CANCELLED).delay()

                print('caopenmeetings deleted')
                # delete all corporate announcements
                CorporateAnnouncement.query.filter(
                    CorporateAnnouncement.account_id.in_(ids)).update(
                    {'deleted': True}, synchronize_session=False)
                db.session.commit()
                print('corporate announcement deleted')

                # delete contacts and contact requests and insert in history
                if del_user_ids:
                    contacts = Contact.query.filter(
                        or_(Contact.sent_by.in_(del_user_ids),
                            Contact.sent_to.in_(del_user_ids)))
                    for contact in list(contacts):
                        data, errors = ContactHistorySchema().load(
                            {'sent_by': contact.sent_by,
                             'sent_to': contact.sent_to})
                        if errors:
                            print(errors, contact)
                            continue
                        db.session.add(data)
                        if count >= batch_size:
                            db.session.commit()
                            count = 0

                    contacts.delete(synchronize_session=False)

                    contact_reqs = ContactRequest.query.filter(
                        or_(ContactRequest.sent_by.in_(del_user_ids),
                            ContactRequest.sent_to.in_(del_user_ids)))
                    for contact_req in list(contact_reqs):
                        data, errors = ContactRequestHistorySchema().load(
                            {'sent_by': contact_req.sent_by,
                             'sent_to': contact_req.sent_to,
                             'status': contact_req.status})
                        if errors:
                            print(errors, contact_req)
                            continue
                        db.session.add(data)
                        if count >= batch_size:
                            db.session.commit()
                            count = 0

                    contact_reqs.delete(synchronize_session=False)

                if count:
                    db.session.commit()

            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
