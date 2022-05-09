"""
Corporate access email related tasks, for each type of email
"""

import time
import os
import shutil

from flask import current_app
from sqlalchemy import and_

from app import db
from app.common.helpers import generate_event_book_email_link
from app.common.utils import delete_fs_file
from app.resources.account_settings.helpers import verify_email
from app.corporate_access_resources.corporate_access_events.models import (
    CorporateAccessEvent)
from app.corporate_access_resources.corporate_access_event_slots.\
    models import CorporateAccessEventSlot
from app.corporate_access_resources.corporate_access_event_invitees.\
    models import CorporateAccessEventInvitee
from app.corporate_access_resources.corporate_access_event_collaborators.\
    models import CorporateAccessEventCollaborator
from app.corporate_access_resources.corporate_access_event_rsvps.models\
    import CorporateAccessEventRSVP
from app.corporate_access_resources.corporate_access_event_participants.\
    models import CorporateAccessEventParticipant
from app.corporate_access_resources.corporate_access_event_hosts.\
    models import CorporateAccessEventHost
from app.resources.users.models import User
from app.corporate_access_resources.corporate_access_event_attendees.\
    models import CorporateAccessEventAttendee
from app.corporate_access_resources.corporate_access_event_inquiries.\
    models import CorporateAccessEventInquiry
from app.corporate_access_resources.corporate_access_event_inquiries \
    import constants as INQUIRIES
from app.resources.unsubscriptions.models import Unsubscription
from app.resources.email_credentials.helpers import get_smtp_settings
from app.common.helpers import generate_ics_file

from queueapp.corporate_accesses.email_contents import (
    EventCompletionContent, LaunchContent, SlotUpdatedContent,
    SlotTimeChangeContent, SlotDeletedContent, SlotInquiryGenerationContent,
    SlotInquiryConfirmationContent, SlotInquiryDeletionContent,
    EventUpdateContent, CancellationContent)
from queueapp.tasks import celery_app, logger, send_email_actual
from app.resources.unsubscriptions.helpers import is_unsubscription
from app.base import constants as APP


@celery_app.task(bind=True, ignore_result=True)
def send_corporate_access_event_launch_email(
        self, result, row_id, *args, **kwargs):
    """
    Sends the corporate access event related email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the corporate_access_event for which email is to be
        generated
    """

    if result:
        try:
            cae = CorporateAccessEvent.query.get(row_id)
            if cae is None:
                logger.exception('Corporate Access Event does not exist')
                return False
            # generate the email content
            # default sender details
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            # get the sender details, incase it is set in account_settings
            acc_setts = cae.account.settings  # account settings
            if (acc_setts.event_sender_email and
                    acc_setts.event_sender_name and acc_setts.verified_status):
                # #TODO: always reverify, before sending
                """
                verify_result = verify_email(acc_setts, reverify=True)
                acc_setts = verify_result['account_settings']"""
                if acc_setts.verified_status:
                    from_name = acc_setts.event_sender_name
                    from_email = acc_setts.event_sender_email
                """else:
                    logger.exception(verify_result['extra_message'])
                db.session.add(acc_setts)
                db.session.commit()"""
            # when creator want to send mail to CAEvent supporter
            ca_support_name = current_app.config['DEFAULT_CA_SUPPORT_NAME']
            ca_support_email = current_app.config['DEFAULT_CA_SUPPORT_EMAIL']
            bcc_addresses = []
            reply_to = ''

            # initialize
            content_getter = LaunchContent(cae)
            subject = ''
            html = ''
            attachment = ''
            body = ''
            # cc email list
            cc_emails = []
            if cae.cc_emails:
                cc_emails = list(set(cae.cc_emails))
            # first send to creator
            creator_email = cae.creator.email
            creator_name = cae.creator.profile.first_name
            time_zone = cae.creator.settings.timezone or\
                current_app.config['USER_DEFAULT_TIMEZONE']
            to_addresses = [creator_email]
            # check unsubscription for user
            is_unsub = is_unsubscription(creator_email, APP.EVNT_CA_EVENT)
            smtp_settings = get_smtp_settings(cae.created_by)
            location = ""
            if cae.city:
                location += cae.city + " "
            if cae.state:
                location += cae.state + " "
            if cae.country:
                location += cae.country
            ics_param = {
                "summery": cae.title,
                "category": cae.event_sub_type.name,
                "dtstart": cae.started_at,
                "dtend": cae.ended_at,
                "description": cae.description,
                "location": location}
            ics_file = generate_ics_file(**ics_param)
            # #TODO: send mail to creator if its not been sent early.
            if (not is_unsub and 'not_for_creator' in kwargs and
                    not kwargs['not_for_creator']):
                # content for creator
                # if meeting type event
                if cae.event_type.is_meeting:
                    subject, body, attachment, html, creator_name = \
                        content_getter.get_meeting_type_creator_content(
                            creator_name, cae, time_zone, creator_email)
                    bcc_addresses = current_app.config['DEFAULT_ADMIN_EMAILS']
                # if normal event type
                else:
                    subject, body, attachment, html, creator_name = \
                        content_getter.get_creator_content(
                            creator_name, cae, time_zone, creator_email)
                send_email_actual(
                    subject=subject,
                    keywords=APP.CORPORATE_EMAIL_TASK,
                    from_name=from_name, from_email=from_email,
                    to_addresses=to_addresses, cc_addresses=cc_emails,
                    bcc_addresses=bcc_addresses, reply_to=reply_to, body=body,
                    html=html, attachment=attachment,
                    smtp_settings=smtp_settings, ics_file=ics_file)
            result = True
            # send emails to invitees
            invitees = CorporateAccessEventInvitee.query.filter_by(
                corporate_access_event_id=row_id,
                email_status=APP.EMAIL_NOT_SENT).all()
            if invitees:
                for invitee in invitees:
                    if invitee.invitee_id:
                        invited_user = User.query.filter_by(
                            row_id=invitee.invitee_id).first()
                        invitee_email = invited_user.email
                        invitee_name = invited_user.profile.first_name
                        time_zone = invited_user.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    else:
                        invitee_email = invitee.invitee_email
                        invitee_name = invitee.invitee_first_name
                        time_zone = cae.creator.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [invitee_email]
                    # check unsubscription for user
                    is_unsub = is_unsubscription(
                        invitee_email,APP.EVNT_CA_EVENT, invitee)
                    if not is_unsub:
                        # content for invitee
                        if cae.event_type.is_meeting:
                            subject, body, attachment, html, invitee_name =\
                                content_getter.\
                                get_meeting_type_invitee_content(
                                    invitee_name, cae, time_zone, invitee,
                                    invitee_email)
                        else:
                            subject, body, attachment, html, invitee_name = \
                                content_getter.get_invitee_content(
                                    invitee_name, cae, time_zone, invitee,
                                    invitee_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, cc_addresses=cc_emails,
                            body=body, html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)
                        # for mail sent or not to invitee
                        invitee.email_status = APP.EMAIL_SENT
                        invitee.is_mail_sent = True
                        db.session.add(invitee)
                        db.session.commit()
                        time.sleep(1)
                    result = True
            # if meeting type event and event_support is true then
            # event support also sent mail
            if cae.event_type.is_meeting and cae.caevent_support:
                invitee = None
                subject, body, attachment, html, invitee_name = \
                    content_getter.get_meeting_type_invitee_content(
                        ca_support_name, cae, time_zone, invitee)
                send_email_actual(
                    subject=subject, from_name=from_name,
                    keywords=APP.CORPORATE_EMAIL_TASK,
                    from_email=from_email, to_addresses=[ca_support_email],
                    reply_to=reply_to, body=body,
                    html=html, attachment=attachment,
                    smtp_settings=smtp_settings)
            # if event is meeting type then return true
            if cae.event_type.is_meeting:
                return True
            # send emails to collaborators
            collaborators = CorporateAccessEventCollaborator.query.filter_by(
                corporate_access_event_id=row_id,
                email_status=APP.EMAIL_NOT_SENT).all()
            if collaborators:
                for collaborator in collaborators:
                    collaborated_user = User.query.filter_by(
                        row_id=collaborator.collaborator_id).first()
                    collaborator_email = collaborated_user.email
                    collaborator_name =\
                        collaborated_user.profile.first_name
                    time_zone = collaborated_user.settings.timezone or\
                        current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [collaborator_email]

                    # check unsubscription for user
                    is_unsub = is_unsubscription(
                        collaborator_email, APP.EVNT_CA_EVENT, collaborator)
                    if not is_unsub:
                        # content for collaborators
                        subject, body, attachment, html, collaborator_name =\
                            content_getter.get_collaborator_content(
                                collaborator_name, cae, time_zone,
                                collaborator_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, cc_addresses=cc_emails,
                            body=body, html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)
                        # for mail sent or not to user
                        collaborator.email_status = APP.EMAIL_SENT
                        collaborator.is_mail_sent = True
                        db.session.add(collaborator)
                        db.session.commit()
                        time.sleep(1)
                    result = True
            # send emails to rsvps
            rsvps = CorporateAccessEventRSVP.query.filter_by(
                corporate_access_event_id=row_id,
                email_status=APP.EMAIL_NOT_SENT).all()
            if rsvps:
                for rsvp in rsvps:
                    rsvp_email = rsvp.email
                    # if rsvp is the creator do not send email again to creator
                    if rsvp_email == cae.creator.email:
                        continue
                    to_addresses = [rsvp_email]
                    rsvp_name = rsvp.contact_person
                    time_zone = None

                    # check unsubscription for user
                    is_unsub = is_unsubscription(
                        rsvp_email, APP.EVNT_CA_EVENT, rsvp)
                    if not is_unsub:
                        # content for rsvps
                        subject, body, attachment, html, rsvp_name =\
                            content_getter.get_rsvp_content(
                                rsvp_name, cae, time_zone, rsvp_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, cc_addresses=cc_emails,
                            body=body, html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)
                        # for mail sent or not to user
                        rsvp.email_status = APP.EMAIL_SENT
                        rsvp.is_mail_sent = True
                        db.session.add(rsvp)
                        db.session.commit()
                        time.sleep(1)
                    result = True
            # send emails to participants
            participants = CorporateAccessEventParticipant.query.filter_by(
                corporate_access_event_id=row_id,
                email_status=APP.EMAIL_NOT_SENT).all()
            if participants:
                for participant in participants:
                    if participant.participant_id:
                        # if participant is the creator do not
                        # send email again to creator
                        if participant.participant_id == cae.creator.row_id:
                            continue
                        participant_user = User.query.filter_by(
                            row_id=participant.participant_id).first()
                        participant_email = participant_user.email
                        participant_name = participant_user.profile.first_name
                        time_zone = participant_user.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    else:
                        participant_email = participant.participant_email
                        participant_name = participant.participant_first_name
                        time_zone = cae.creator.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [participant_email]

                    # check unsubscription for user
                    is_unsub = is_unsubscription(
                        participant_email, APP.EVNT_CA_EVENT, participant)
                    if not is_unsub:
                        # content for participants
                        subject, body, attachment, html, participant_name =\
                            content_getter.get_participant_content(
                                participant_name, cae, time_zone,
                                participant_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, cc_addresses=cc_emails,
                            body=body, html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)
                        # for mail sent or not to user
                        participant.email_status = APP.EMAIL_SENT
                        participant.is_mail_sent = True
                        db.session.add(participant)
                        db.session.commit()
                        time.sleep(1)
                    result = True
            # send emails to hosts
            hosts = CorporateAccessEventHost.query.filter_by(
                corporate_access_event_id=row_id,
                email_status=APP.EMAIL_NOT_SENT).all()
            if hosts:
                for host in hosts:
                    if host.host_id:
                        # if host is the creator do not
                        # send email again to creator
                        if host.host_id == cae.creator.row_id:
                            continue
                        host_user = User.query.filter_by(
                            row_id=host.host_id).first()
                        host_email = host_user.email
                        host_name = host_user.profile.first_name
                        time_zone = host_user.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    else:
                        host_email = host.host_email
                        host_name = host.host_first_name
                        time_zone = cae.creator.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [host_email]

                    # check unsubscription for user
                    is_unsub = is_unsubscription(
                        host_email, APP.EVNT_CA_EVENT, host)
                    if not is_unsub:
                        # content for hosts
                        subject, body, attachment, html, host_name =\
                            content_getter.get_host_content(
                                host_name, cae, time_zone, host_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, cc_addresses=cc_emails,
                            body=body, html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)
                        # for mail sent or not to user
                        host.email_status = APP.EMAIL_SENT
                        host.is_mail_sent = True
                        db.session.add(host)
                        db.session.commit()
                        time.sleep(1)
                        result = True
            if content_getter.attachment:
                delete_fs_file(content_getter.attachment)
            # will delete folder containing ics_file
            shutil.rmtree(os.path.dirname(ics_file))

        except Exception as e:
            raise e
            logger.exception(e)
            result = False

        finally:
            cae.is_in_process = False
            db.session.add(cae)
            db.session.commit()

    return result


@celery_app.task(bind=True, ignore_result=True)
def send_corporate_access_event_new_invitee_email(
        self, result, row_id, invitee_list, invitee_ids, *args, **kwargs):
    """
    Sends the corporate access event new invitee email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the corporate_access_event for which email is to be
        generated
    """
    if result:
        try:
            cae = CorporateAccessEvent.query.get(row_id)
            if cae is None:
                logger.exception('Corporate Access Event does not exist')
                return False
            # generate the email content
            # default sender details
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            # get the sender details, incase it is set in account_settings
            acc_setts = cae.account.settings  # account settings
            if (acc_setts.event_sender_email and
                    acc_setts.event_sender_name and acc_setts.verified_status):
                # #TODO: always reverify, before sending
                """
                verify_result = verify_email(acc_setts, reverify=True)
                acc_setts = verify_result['account_settings']"""
                if acc_setts.verified_status:
                    from_name = acc_setts.event_sender_name
                    from_email = acc_setts.event_sender_email
                """else:
                    logger.exception(verify_result['extra_message'])
                db.session.add(acc_setts)
                db.session.commit()"""
            location = ""
            if cae.city:
                location += cae.city + " "
            if cae.state:
                location += cae.state + " "
            if cae.country:
                location += cae.country
            ics_param = {
                "summery": cae.title,
                "category": cae.event_sub_type.name,
                "dtstart": cae.started_at,
                "dtend": cae.ended_at,
                "description": cae.description,
                "location": location}
            ics_file = generate_ics_file(**ics_param)
            # when creator want to send mail to CAEvent supporter
            reply_to = ''

            # initialize
            content_getter = LaunchContent(cae)
            subject = ''
            html = ''
            attachment = ''
            body = ''
            # cc email list
            cc_emails = []
            if cae.cc_emails:
                cc_emails = list(set(cae.cc_emails))
            # send emails to invitees
            invitees = CorporateAccessEventInvitee.query.filter_by(
                corporate_access_event_id=row_id,
                email_status=APP.EMAIL_NOT_SENT).all()
            if invitees:
                for invitee in invitees:
                    if invitee.invitee_id:
                        if invitee.invitee_id not in invitee_ids:
                            continue
                        invited_user = User.query.filter_by(
                            row_id=invitee.invitee_id).first()
                        invitee_email = invited_user.email
                        invitee_name = invited_user.profile.first_name
                        time_zone = invited_user.settings.timezone or \
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    else:
                        if invitee.invitee_email not in invitee_list:
                            continue
                        invitee_email = invitee.invitee_email
                        invitee_name = invitee.invitee_first_name
                        time_zone = cae.creator.settings.timezone or \
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [invitee_email]
                    is_unsub = is_unsubscription(
                        invitee_email, APP.EVNT_CA_EVENT, invitee)

                    if is_unsub:
                        continue
                    smtp_settings = get_smtp_settings(cae.created_by)
                    # content for invitee
                    if cae.event_type.is_meeting:
                        subject, body, attachment, html, invitee_name = \
                            content_getter.get_meeting_type_invitee_content(
                                invitee_name, cae, time_zone, invitee,
                                invitee_email)
                    else:
                        subject, body, attachment, html, invitee_name = \
                            content_getter.get_invitee_content(
                                invitee_name, cae, time_zone, invitee,
                                invitee_email)

                    send_email_actual(
                        subject=subject, from_name=from_name,
                        keywords=APP.CORPORATE_EMAIL_TASK,
                        from_email=from_email, to_addresses=to_addresses,
                        reply_to=reply_to, cc_addresses=cc_emails, body=body,
                        html=html, attachment=attachment,
                        smtp_settings=smtp_settings, ics_file=ics_file)
                    # for mail sent or not to user
                    invitee.email_status = APP.EMAIL_SENT
                    invitee.is_mail_sent = True
                    db.session.add(invitee)
                    db.session.commit()
                result = True
            if content_getter.attachment:
                delete_fs_file(content_getter.attachment)
            # will delete folder containing ics_file
            shutil.rmtree(os.path.dirname(ics_file))
        except Exception as e:
            raise e
            logger.exception(e)
            result = False

        finally:
            cae.is_in_process = False
            db.session.add(cae)
            db.session.commit()



        return result


@celery_app.task(bind=True, ignore_result=True)
def send_corporate_access_event_completion_email(
        self, result, row_id, *args, **kwargs):
    """
    Sends the corporate access event related email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the corporate_access_event for which email is to be
        generated
    """

    if result:
        try:
            cae = CorporateAccessEvent.query.get(row_id)
            if cae is None:
                logger.exception('Corporate Access Event does not exist')
                return False
            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            # initialize
            content_getter = EventCompletionContent(cae)
            subject = ''
            html = ''
            attachment = ''
            body = ''

            smtp_settings = get_smtp_settings(cae.created_by)
            # send emails to attendees
            attendees = CorporateAccessEventAttendee.query.filter_by(
                corporate_access_event_id=row_id).all()
            if attendees:
                for attendee in attendees:
                    attendee_user = User.query.filter_by(
                        row_id=attendee.attendee_id).first()
                    attendee_email = attendee_user.email
                    attendee_name = attendee_user.profile.first_name
                    to_addresses = [attendee_email]
                    is_unsub = is_unsubscription(
                        attendee_email, APP.EVNT_CA_EVENT)
                    if not is_unsub:
                        # content for invitee
                        subject, body, attachment, html, attendee_name =\
                            content_getter.get_attendee_content(
                                attendee_name, cae, attendee_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings)
                        result = True

            # send emails to participants
            participants = CorporateAccessEventParticipant.query.filter_by(
                corporate_access_event_id=row_id).all()
            if participants:
                for participant in participants:
                    if participant.participant_id:
                        # if participant is the creator do not
                        # send email again to creator
                        if participant.participant_id == cae.creator.row_id:
                            continue
                        participant_user = User.query.filter_by(
                            row_id=participant.participant_id).first()
                        participant_email = participant_user.email
                        participant_name = participant_user.profile.first_name
                    else:
                        participant_email = participant.participant_email
                        participant_name = participant.participant_first_name
                    to_addresses = [participant_email]
                    is_unsub = is_unsubscription(
                        participant_email, APP.EVNT_CA_EVENT)
                    if not is_unsub:
                        # content for participants
                        subject, body, attachment, html, participant_name =\
                            content_getter.get_participant_content(
                                participant_name, cae, participant_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings)
                        result = True

        except Exception as e:
            raise e
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def send_corporate_access_event_updated_email(
        self, result, row_id, *args, **kwargs):
    """
    Sends the corporate access event related email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the corporate_access_event for which email is to be
        generated
    """

    if result:
        try:
            cae = CorporateAccessEvent.query.get(row_id)
            if cae is None:
                logger.exception('Corporate Access Event does not exist')
                return False
            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            location = ""
            if cae.city:
                location += cae.city + " "
            if cae.state:
                location += cae.state + " "
            if cae.country:
                location += cae.country
            ics_param = {
                "summery": cae.title,
                "category": cae.event_sub_type.name,
                "dtstart": cae.started_at,
                "dtend": cae.ended_at,
                "description": cae.description,
                "location": location}
            ics_file = generate_ics_file(**ics_param)
            # initialize
            content_getter = EventUpdateContent(cae)
            subject = ''
            html = ''
            attachment = ''
            body = ''
            # cc email list
            cc_emails = []
            if cae.cc_emails:
                cc_emails = list(set(cae.cc_emails))
            # first send to creator
            creator_email = cae.creator.email
            creator_name = cae.creator.profile.first_name
            time_zone = cae.creator.settings.timezone or\
                current_app.config['USER_DEFAULT_TIMEZONE']
            to_addresses = [creator_email]
            is_unsub = is_unsubscription(
                creator_email, APP.EVNT_CA_EVENT)
            smtp_settings = get_smtp_settings(cae.created_by)
            if not is_unsub:
                # content for creator
                subject, body, attachment, html, creator_name = content_getter.\
                    get_creator_content(creator_name, cae, time_zone,
                        creator_email)
                send_email_actual(
                    subject=subject, keywords=APP.CORPORATE_EMAIL_TASK,
                    from_name=from_name, from_email=from_email,
                    to_addresses=to_addresses, cc_addresses=cc_emails,
                    reply_to=reply_to, body=body, html=html,
                    attachment=attachment, smtp_settings=smtp_settings,
                    ics_file=ics_file)
                result = True
            # send emails to invitees
            invitees = CorporateAccessEventInvitee.query.filter_by(
                corporate_access_event_id=row_id).all()
            if invitees:
                for invitee in invitees:
                    if invitee.invitee_id:
                        invited_user = User.query.filter_by(
                            row_id=invitee.invitee_id).first()
                        invitee_email = invited_user.email
                        invitee_name = invited_user.profile.first_name
                        time_zone = invited_user.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    else:
                        invitee_email = invitee.invitee_email
                        invitee_name = invitee.invitee_first_name
                        time_zone = cae.creator.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [invitee_email]
                    is_unsub = is_unsubscription(
                        invitee_email, APP.EVNT_CA_EVENT)
                    if not is_unsub:
                        # content for invitee
                        subject, body, attachment, html, invitee_name =\
                            content_getter.get_invitee_content(
                                invitee_name, cae, time_zone, invitee,
                                invitee_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, cc_addresses=cc_emails, body=body,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)
                        result = True
            # send emails to collaborators
            collaborators = CorporateAccessEventCollaborator.query.filter_by(
                corporate_access_event_id=row_id).all()
            if collaborators:
                for collaborator in collaborators:
                    collaborated_user = User.query.filter_by(
                        row_id=collaborator.collaborator_id).first()
                    collaborator_email = collaborated_user.email
                    collaborator_name =\
                        collaborated_user.profile.first_name
                    time_zone = collaborated_user.settings.timezone or\
                        current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [collaborator_email]
                    is_unsub = is_unsubscription(
                        collaborator_email, APP.EVNT_CA_EVENT)
                    if not is_unsub:
                        # content for collaborators
                        subject, body, attachment, html, collaborator_name =\
                            content_getter.get_collaborator_content(
                                collaborator_name, cae, time_zone,
                                collaborator_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body,
                            html=html, cc_addresses=cc_emails,
                            attachment=attachment, smtp_settings=smtp_settings,
                            ics_file=ics_file)
                        result = True
            # send emails to rsvps
            rsvps = CorporateAccessEventRSVP.query.filter_by(
                corporate_access_event_id=row_id).all()
            if rsvps:
                for rsvp in rsvps:
                    rsvp_email = rsvp.email
                    to_addresses = [rsvp_email]
                    # if rsvp is the creator do not send email again to creator
                    if rsvp_email == cae.creator.email:
                        continue
                    rsvp_name = rsvp.contact_person
                    is_unsub = is_unsubscription(
                        rsvp_email, APP.EVNT_CA_EVENT)
                    if not is_unsub:
                        # content for rsvps
                        subject, body, attachment, html, rsvp_name =\
                            content_getter.get_rsvp_content(
                                rsvp_name, cae, time_zone, rsvp_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, cc_addresses=cc_emails, body=body,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)
                        result = True
            # send emails to participants
            participants = CorporateAccessEventParticipant.query.filter_by(
                corporate_access_event_id=row_id).all()
            if participants:
                for participant in participants:
                    if participant.participant_id:
                        # if participant is the creator do not
                        # send email again to creator
                        if participant.participant_id == cae.creator.row_id:
                            continue
                        participant_user = User.query.filter_by(
                            row_id=participant.participant_id).first()
                        participant_email = participant_user.email
                        participant_name = participant_user.profile.first_name
                        time_zone = participant_user.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    else:
                        participant_email = participant.participant_email
                        participant_name = participant.participant_first_name
                        time_zone = cae.creator.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [participant_email]
                    is_unsub = is_unsubscription(
                        participant_email, APP.EVNT_CA_EVENT)
                    if not is_unsub:
                        # content for participants
                        subject, body, attachment, html, participant_name =\
                            content_getter.get_participant_content(
                                participant_name, cae, time_zone,
                                participant_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, cc_addresses=cc_emails, body=body,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)
                        result = True
            # # send emails to hosts
            hosts = CorporateAccessEventHost.query.filter_by(
                corporate_access_event_id=row_id).all()
            if hosts:
                for host in hosts:
                    if host.host_id:
                        # if host is the creator do not
                        # send email again to creator
                        if host.host_id == cae.creator.row_id:
                            continue
                        host_user = User.query.filter_by(
                            row_id=host.host_id).first()
                        host_email = host_user.email
                        host_name = host_user.profile.first_name
                        time_zone = host_user.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    else:
                        host_email = host.host_email
                        host_name = host.host_first_name
                        time_zone = cae.creator.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [host_email]
                    is_unsub = is_unsubscription(
                        host_email, APP.EVNT_CA_EVENT)
                    if not is_unsub:
                        # content for hosts
                        subject, body, attachment, html, host_name =\
                            content_getter.get_host_content(
                                host_name, cae, time_zone, host_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, cc_addresses=cc_emails, body=body,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)
                        result = True
            # will delete folder containing ics_file
            shutil.rmtree(os.path.dirname(ics_file))
        except Exception as e:
            raise e
            logger.exception(e)
            result = False

    return result


# #TODO: to be discussed and done
@celery_app.task(bind=True, ignore_result=True)
def send_corporate_access_event_collaborator_added_email(
        self, result, row_id, *args, **kwargs):
    """
    Sends the corporate access event related email

    :param result:
        the result of previous task when chaining. Remember to pass True,
        when called as first of chain, or individually.
    :param row_id:
        the row id of the corporate_access_event for which email is to be
        generated
    """

    if result:
        try:
            cae = CorporateAccessEvent.query.get(row_id)
            if cae is None:
                logger.exception('Corporate Access Event does not exist')
                return False
            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            # initialize
            content_getter = EventUpdateContent(self)
            subject = ''
            html = ''
            attachment = ''
            body = ''

            # first send to creator
            creator_email = cae.creator.email
            creator_name = cae.creator.profile.first_name
            to_addresses = [creator_email]

            time_zone = cae.creator.settings.timezone or \
                        current_app.config['USER_DEFAULT_TIMEZONE']
            is_unsub = is_unsubscription(
                creator_email, APP.EVNT_CA_EVENT)
            smtp_settings = get_smtp_settings(cae.created_by)
            if not is_unsub:
                # content for creator
                subject, body, attachment, html, creator_name = content_getter.\
                    get_creator_content(creator_name, cae,
                        time_zone, creator_email)
                send_email_actual(
                    subject=subject, keywords=APP.CORPORATE_EMAIL_TASK,
                    from_name=from_name, from_email=from_email,
                    to_addresses=to_addresses, reply_to=reply_to, body=body,
                    html=html, attachment=attachment,
                    smtp_settings=smtp_settings)
            result = True
            # send emails to invitees
            invitees = CorporateAccessEventInvitee.query.filter_by(
                corporate_access_event_id=row_id).all()
            if invitees:
                for invitee in invitees:
                    if invitee.invitee_id:
                        invited_user = User.query.filter_by(
                            row_id=invitee.invitee_id).first()
                        invitee_email = invited_user.email
                        invitee_name = invited_user.profile.first_name
                    else:
                        invitee_email = invitee.invitee_email
                        invitee_name = invitee.invitee_first_name
                    to_addresses = [invitee_email]

                    is_unsub = is_unsubscription(
                        invitee_email, APP.EVNT_CA_EVENT)
                    if not is_unsub:
                        # content for invitee
                        subject, body, attachment, html, invitee_name =\
                            content_getter.get_invitee_content(invitee_name,
                                cae, time_zone, invitee, invitee_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings)
                    result = True
            # send emails to collaborators
            collaborators = CorporateAccessEventCollaborator.query.filter_by(
                corporate_access_event_id=row_id).all()
            if collaborators:
                for collaborator in collaborators:
                    collaborated_user = User.query.filter_by(
                        row_id=collaborator.collaborator_id).first()
                    collaborator_email = collaborated_user.email
                    collaborator_name =\
                        collaborated_user.profile.first_name
                    to_addresses = [collaborator_email]
                    is_unsub = is_unsubscription(
                        collaborator_email, APP.EVNT_CA_EVENT)
                    if not is_unsub:
                        # content for collaborators
                        subject, body, attachment, html, collaborator_name =\
                            content_getter.get_collaborator_content(
                                collaborator_name, cae, time_zone,
                                collaborator_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings)
                    result = True
            # send emails to rsvps
            rsvps = CorporateAccessEventRSVP.query.filter_by(
                corporate_access_event_id=row_id).all()
            if rsvps:
                for rsvp in rsvps:
                    rsvp_email = rsvp.email
                    to_addresses = [rsvp_email]
                    rsvp_name = rsvp.contact_person
                    is_unsub = is_unsubscription(
                        rsvp_email, APP.EVNT_CA_EVENT)
                    if not is_unsub:
                        # content for rsvps
                        subject, body, attachment, html, rsvp_name =\
                            content_getter.get_rsvp_content(rsvp_name, cae,
                                time_zone, rsvp_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings)
                    result = True
            # send emails to participants
            participants = CorporateAccessEventParticipant.query.filter_by(
                corporate_access_event_id=row_id).all()
            if participants:
                for participant in participants:
                    if participant.participant_id:
                        participant_user = User.query.filter_by(
                            row_id=participant.participant_id).first()
                        participant_email = participant_user.email
                        participant_name = participant_user.profile.first_name
                    else:
                        participant_email = participant.participant_email
                        participant_name = participant.participant_first_name
                    to_addresses = [participant_email]
                    is_unsub = is_unsubscription(
                        participant_email, APP.EVNT_CA_EVENT)
                    if not is_unsub:
                        # content for participants
                        subject, body, attachment, html, participant_name =\
                            content_getter.get_participant_content(
                                participant_name, cae, time_zone,
                                participant_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings)
                    result = True
            # # send emails to hosts
            # hosts = CorporateAccessEventHost.query.filter_by(
            #     corporate_access_event_id=row_id).all()
            # if hosts:
            #     for host in hosts:
            #         if host.host_id:
            #             host_user = User.query.filter_by(
            #                 row_id=host.host_id).first()
            #             host_email = host_user.email
            #             host_name = host_user.profile.first_name
            #         else:
            #             host_email = host.host_email
            #             host_name = host.host_first_name
            #         to_addresses = [host_email]
            #         # content for hosts
            #         subject, body, attachment, html, host_name =\
            #             content_getter.get_host_content(host_name)
            #         send_email_actual(
            #             subject=subject, from_name=from_name,
            #             from_email=from_email, to_addresses=to_addresses,
            #             reply_to=reply_to, body=body,
            #             html=html, attachment=attachment)
            #         result = True
        except Exception as e:
            raise e
            logger.exception(e)
            result = False

    return result


# #TODO: need to be discussed
@celery_app.task(bind=True, ignore_result=True)
def send_corporate_access_event_slot_time_change_email(
        self, result, row_id, cae_id, *args, **kwargs):
    """
    Sends the corporate access event slot time change related email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the slot for which email is to be generated
    :param cae_id:
        the row id of the corporate_access_event for which email is to be
        generated
    """
    if result:
        try:
            cae = CorporateAccessEvent.query.get(cae_id)
            if cae is None:
                logger.exception('Corporate Access Event does not exist')
                return False
            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            # initialize
            content_getter = SlotTimeChangeContent(self)
            subject = ''
            html = ''
            attachment = ''
            body = ''

            smtp_settings = get_smtp_settings(cae.created_by)
            # first send to creator
            creator_email = cae.creator.email
            creator_name = cae.creator.profile.first_name
            to_addresses = [creator_email]
            is_unsub = is_unsubscription(
                creator_email, APP.EVNT_CA_EVENT)
            if not is_unsub:
                # content for creator
                subject, body, attachment, html, creator_name = content_getter.\
                    get_creator_content(creator_name)
                send_email_actual(
                    subject=subject, keywords=APP.CORPORATE_EMAIL_TASK,
                    from_name=from_name, from_email=from_email,
                    to_addresses=to_addresses, reply_to=reply_to, body=body,
                    html=html, attachment=attachment,
                    smtp_settings=smtp_settings)
            result = True

            # send emails to collaborators
            collaborators = CorporateAccessEventCollaborator.query.filter_by(
                corporate_access_event_id=cae_id).all()
            if collaborators:
                for collaborator in collaborators:
                    collaborated_user = User.query.filter_by(
                        row_id=collaborator.collaborator_id).first()
                    collaborator_email = collaborated_user.email
                    collaborator_name =\
                        collaborated_user.profile.first_name
                    to_addresses = [collaborator_email]
                    is_unsub = is_unsubscription(
                        collaborator_email, APP.EVNT_CA_EVENT)
                    if not is_unsub:
                        # content for collaborators
                        subject, body, attachment, html, collaborator_name =\
                            content_getter.get_collaborator_content(
                                collaborator_name)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings)
                    result = True

            # send emails to slot inquirers
            slot_inquirers = CorporateAccessEventInquiry.query.filter_by(
                corporate_access_event_id=cae_id,
                corporate_access_event_slot_id=row_id,
                status=INQUIRIES.CONFIRMED).all()
            if slot_inquirers:
                for slot_inquirer in slot_inquirers:
                    slot_inquirer_user = User.query.filter_by(
                        row_id=slot_inquirer.created_by).first()
                    slot_inquirer_email = slot_inquirer_user.email
                    slot_inquirer_name = slot_inquirer_user.profile.first_name
                    to_addresses = [slot_inquirer_email]
                    is_unsub = is_unsubscription(
                        slot_inquirer_email, APP.EVNT_CA_EVENT)
                    if not is_unsub:
                        # content for collaborators
                        subject, body, attachment, html, slot_inquirer_name =\
                            content_getter.get_slot_inquirer_content(
                                slot_inquirer_name)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings)
                    result = True

        except Exception as e:
            raise e
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def send_corporate_access_event_slot_updated_email(
        self, result, row_id, cae_id, *args, **kwargs):
    """
    Sends the corporate access event slot updated related email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the slot for which email is to be generated
    :param cae_id:
        the row id of the corporate_access_event for which email is to be
        generated
    """
    if result:
        try:
            cae = CorporateAccessEvent.query.get(cae_id)
            cae_slot = CorporateAccessEventSlot.query.get(row_id)
            if cae is None:
                logger.exception('Corporate Access Event does not exist')
                return False
            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            # initialize
            content_getter = SlotUpdatedContent(cae)
            subject = ''
            html = ''
            attachment = ''
            body = ''
            # cc email list
            cc_emails = []
            if cae.cc_emails:
                cc_emails = list(set(cae.cc_emails))
            # generate event url for login or registration
            # event_url = generate_event_book_email_link(
            #     current_app.config['CORPACCS_EVENT_JOIN_ADD_URL'], cae_id)

            smtp_settings = get_smtp_settings(cae.created_by)
            # first send to creator
            creator_email = cae.creator.email
            creator_name = cae.creator.profile.first_name
            time_zone = cae.creator.settings.timezone or\
                current_app.config['USER_DEFAULT_TIMEZONE']
            to_addresses = [creator_email]
            is_unsub = is_unsubscription(
                creator_email, APP.EVNT_CA_EVENT)
            if not is_unsub:
                # content for creator
                subject, body, attachment, html, creator_name = content_getter.\
                    get_creator_content(
                        creator_name, cae, cae_slot, time_zone, creator_email)
                send_email_actual(
                    subject=subject, keywords=APP.CORPORATE_EMAIL_TASK,
                    from_name=from_name, from_email=from_email,
                    to_addresses=to_addresses, reply_to=reply_to, body=body,
                    html=html, attachment=attachment,
                    smtp_settings=smtp_settings)
            result = True

            # send emails to collaborators
            collaborators = CorporateAccessEventCollaborator.query.filter_by(
                corporate_access_event_id=cae_id).all()
            if collaborators:
                for collaborator in collaborators:
                    collaborated_user = User.query.filter_by(
                        row_id=collaborator.collaborator_id).first()
                    collaborator_email = collaborated_user.email
                    collaborator_name =\
                        collaborated_user.profile.first_name
                    to_addresses = [collaborator_email]
                    time_zone = collaborated_user.settings.timezone or\
                        current_app.config['USER_DEFAULT_TIMEZONE']
                    is_unsub = is_unsubscription(
                        collaborator_email, APP.EVNT_CA_EVENT)
                    if not is_unsub:
                        # content for collaborators
                        subject, body, attachment, html, collaborator_name =\
                            content_getter.get_collaborator_content(
                                collaborator_name, cae, cae_slot,
                                time_zone, collaborator_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings)
                    result = True

            # send emails to slot inquirers
            slot_inquirers = CorporateAccessEventInquiry.query.filter_by(
                corporate_access_event_id=cae_id,
                corporate_access_event_slot_id=row_id,
                status=INQUIRIES.CONFIRMED).all()
            if slot_inquirers:
                for slot_inquirer in slot_inquirers:
                    slot_inquirer_user = User.query.filter_by(
                        row_id=slot_inquirer.created_by).first()
                    slot_inquirer_email = slot_inquirer_user.email
                    slot_inquirer_name = slot_inquirer_user.profile.first_name
                    to_addresses = [slot_inquirer_email]
                    time_zone = slot_inquirer_user.settings.timezone or\
                        current_app.config['USER_DEFAULT_TIMEZONE']
                    is_unsub = is_unsubscription(
                        slot_inquirer_email, APP.EVNT_CA_EVENT)
                    if not is_unsub:
                        # content for collaborators
                        subject, body, attachment, html, slot_inquirer_name =\
                            content_getter.get_slot_inquirer_content(
                                slot_inquirer_name, cae, cae_slot, time_zone,
                                slot_inquirer_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body, html=html,
                            attachment=attachment, smtp_settings=smtp_settings)
                    result = True

        except Exception as e:
            raise e
            logger.exception(e)
            result = False

    return result


# #TODO: needed to be discussed
@celery_app.task(bind=True, ignore_result=True)
def send_corporate_access_event_slot_deleted_email(
        self, result, creator_email, creator_name, collaborator_ids,
        slot_inquirer_user_ids, user_id, *args, **kwargs):
    """
    Sends the corporate access event slot deletion related email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param creator_email:
        the email of the user who created corporate_access_event
    :param creator_name:
        the name of the user who created corporate_access_event
    :param collaborator_ids:
        the ids of the collaborators of corporate_access_event
    :param slot_inquirer_user_ids:
        user_ids of slot_inquirers of corporate_access_event
    """
    if result:
        try:
            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            # initialize
            content_getter = SlotDeletedContent(self)
            subject = ''
            html = ''
            attachment = ''
            body = ''

            smtp_settings = get_smtp_settings(user_id)
            # first send to creator
            to_addresses = [creator_email]
            is_unsub = is_unsubscription(
                creator_email, APP.EVNT_CA_EVENT)
            if not is_unsub:
                # content for creator
                subject, body, attachment, html, creator_name = content_getter.\
                    get_creator_content(creator_name)
                send_email_actual(
                    subject=subject, keywords=APP.CORPORATE_EMAIL_TASK,
                    from_name=from_name, from_email=from_email,
                    to_addresses=to_addresses, reply_to=reply_to, body=body,
                    html=html, attachment=attachment,
                    smtp_settings=smtp_settings)
            result = True

            # send emails to collaborators
            if collaborator_ids:
                for collaborator_id in collaborator_ids:
                    collaborated_user = User.query.filter_by(
                        row_id=collaborator_id).first()
                    collaborator_email = collaborated_user.email
                    collaborator_name =\
                        collaborated_user.profile.first_name
                    to_addresses = [collaborator_email]
                    is_unsub = is_unsubscription(
                        collaborator_email, APP.EVNT_CA_EVENT)
                    if not is_unsub:
                        # content for collaborators
                        subject, body, attachment, html, collaborator_name =\
                            content_getter.get_collaborator_content(
                                collaborator_name)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings)
                    result = True

            # send emails to slot inquirers
            if slot_inquirer_user_ids:
                for slot_inquirer_user_id in slot_inquirer_user_ids:
                    slot_inquirer_user = User.query.filter_by(
                        row_id=slot_inquirer_user_id).first()
                    slot_inquirer_email = slot_inquirer_user.email
                    slot_inquirer_name = slot_inquirer_user.profile.first_name
                    to_addresses = [slot_inquirer_email]
                    is_unsub = is_unsubscription(
                        slot_inquirer_email, APP.EVNT_CA_EVENT)
                    if not is_unsub:
                        # content for collaborators
                        subject, body, attachment, html, slot_inquirer_name =\
                            content_getter.get_slot_inquirer_content(
                                slot_inquirer_name)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings)
                    result = True

        except Exception as e:
            raise e
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def send_corporate_access_event_slot_inquiry_generated_email(
        self, result, cae_slot_id, cae_id, inquirer_id, *args, **kwargs):
    """
    Sends the corporate access event slot inquiry generated email

    #TODO: currently unused, recheck and modify before re-enabling

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param cae_slot_id:
        the row id of the corporate_access_event_slot for which email is to be
        generated
    :param cae_id:
        the row id of the corporate_access_event for which email is to be
        generated
    :param inquirer_id:
        the created_by value of inquirer i.e. invitee_id
    """
    if result:
        try:
            # #TODO may be used in future
            return True
            # slot inquiry generated email will not be sent for anyone for now
            cae = CorporateAccessEvent.query.get(cae_id)
            cae_slot = CorporateAccessEventSlot.query.get(cae_slot_id)
            if cae is None:
                logger.exception('Corporate Access Event does not exist')
                return False

            # uncomment the following variables once you
            # enable generated email task
            # generate the email content
            # from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            # from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            # reply_to = ''

            # initialize
            content_getter = SlotInquiryGenerationContent(cae)
            subject = ''
            html = ''
            attachment = ''
            body = ''
            # cc email list
            cc_emails = []
            if cae.cc_emails:
                cc_emails = list(set(cae.cc_emails))
            # generate event url for login or registration
            # event_url = generate_event_book_email_link(
            #     current_app.config['CORPACCS_EVENT_JOIN_ADD_URL'], cae_id)

            smtp_settings = get_smtp_settings(cae.created_by)
            # first send to creator
            creator_email = cae.creator.email
            creator_name = cae.creator.profile.first_name
            time_zone = cae.creator.settings.timezone or\
                current_app.config['USER_DEFAULT_TIMEZONE']
            to_addresses = [creator_email]
            is_unsub = is_unsubscription(
                creator_email, APP.EVNT_CA_EVENT)
            if not is_unsub:
                # content for creator
                subject, body, attachment, html, creator_name = content_getter.\
                    get_creator_content(
                        creator_name, cae, cae_slot, time_zone, creator_email)
                # we are not sending an email to the creator
                # on slot inquiry generation for now
                """
                send_email_actual(
                    subject=subject,
                    from_name=from_name, from_email=from_email,
                    to_addresses=to_addresses, reply_to=reply_to, body=body,
                    html=html, attachment=attachment, 
                    smtp_settings=smtp_settings)
                """
            result = True

            # send emails to collaborators
            collaborators = CorporateAccessEventCollaborator.query.filter_by(
                corporate_access_event_id=cae_id).all()
            if collaborators:
                for collaborator in collaborators:
                    collaborated_user = User.query.filter_by(
                        row_id=collaborator.collaborator_id).first()
                    collaborator_email = collaborated_user.email
                    collaborator_name =\
                        collaborated_user.profile.first_name
                    to_addresses = [collaborator_email]
                    time_zone = collaborated_user.settings.timezone or\
                        current_app.config['USER_DEFAULT_TIMEZONE']
                    is_unsub = is_unsubscription(
                        collaborator_email, APP.EVNT_CA_EVENT)
                    if not is_unsub:
                        # content for collaborators
                        subject, body, attachment, html, collaborator_name =\
                            content_getter.get_collaborator_content(
                                collaborator_name, cae, cae_slot,
                                time_zone, collaborator_email)
                        # we are not sending an email to the collaborator
                        # on slot inquiry generation for now
                        """
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body,
                            html=html, attachment=attachment, 
                            smtp_settings=smtp_settings)
                        """
                    result = True

            # send emails to slot inquirers
            slot_inquirer_user = User.query.filter_by(
                row_id=inquirer_id).first()
            slot_inquirer_email = slot_inquirer_user.email
            slot_inquirer_name = slot_inquirer_user.profile.first_name
            # to_addresses = [slot_inquirer_email]
            time_zone = slot_inquirer_user.settings.timezone or\
                current_app.config['USER_DEFAULT_TIMEZONE']
            is_unsub = is_unsubscription(
                slot_inquirer_email, APP.EVNT_CA_EVENT)
            if not is_unsub:
                # content for collaborators
                subject, body, attachment, html, slot_inquirer_name =\
                    content_getter.get_slot_inquirer_content(
                        slot_inquirer_name, cae, cae_slot, time_zone,
                        slot_inquirer_email)
                # we are not sending an email to the inquirer(creator of inquiry)
                # on slot inquiry generation for now
                """
                send_email_actual(
                    subject=subject, from_name=from_name,
                    from_email=from_email, to_addresses=to_addresses,
                    reply_to=reply_to, body=body,
                    html=html, attachment=attachment, 
                    smtp_settings=smtp_settings)
                """
            result = True

        except Exception as e:
            raise e
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def send_corporate_access_event_slot_inquiry_confirmation_email(
        self, result, cae_slot_id, cae_id, inquirer_id, *args, **kwargs):
    """
    Sends the corporate access event slot inquiry confirmation email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param cae_slot_id:
        the row id of the corporate_access_event_slot for which email is to be
        generated
    :param cae_id:
        the row id of the corporate_access_event for which email is to be
        generated
    :param inquirer_id:
        the created_by value of inquirer i.e. invitee_id
    """
    if result:
        try:
            cae = CorporateAccessEvent.query.get(cae_id)
            cae_slot = CorporateAccessEventSlot.query.get(cae_slot_id)
            if cae is None:
                logger.exception('Corporate Access Event does not exist')
                return False
            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            # initialize
            content_getter = SlotInquiryConfirmationContent(cae)
            subject = ''
            html = ''
            attachment = ''
            body = ''
            # cc email list
            cc_emails = []
            if cae.cc_emails:
                cc_emails = list(set(cae.cc_emails))
            # generate event url for login or registration
            # event_url = generate_event_book_email_link(
            #     current_app.config['CORPACCS_EVENT_JOIN_ADD_URL'], cae_id)
            # we are not sending an email to the creator and the collaborator
            # on slot inquiry confirmation for now
            smtp_settings = get_smtp_settings(cae.created_by)
            """
            # first send to creator
            creator_email = cae.creator.email
            creator_name = cae.creator.profile.first_name
            time_zone = cae.creator.settings.timezone
            to_addresses = [creator_email]
            is_unsub = is_unsubscription(
                        creator_email, APP.EVNT_CA_EVENT)
            if not is_unsub:
                # content for creator
                subject, body, attachment, html, creator_name = content_getter.\
                    get_creator_content(creator_name, cae, cae_slot, time_zone)
                send_email_actual(
                    subject=subject,
                    from_name=from_name, from_email=from_email,
                    to_addresses=to_addresses, reply_to=reply_to, body=body,
                    html=html, attachment=attachment, 
                    smtp_settings=smtp_settings)
            result = True

            # send emails to collaborators
            collaborators = CorporateAccessEventCollaborator.query.filter_by(
                corporate_access_event_id=cae_id).all()
            if collaborators:
                for collaborator in collaborators:
                    collaborated_user = User.query.filter_by(
                        row_id=collaborator.collaborator_id).first()
                    collaborator_email = collaborated_user.email
                    collaborator_name =\
                        collaborated_user.profile.first_name
                    to_addresses = [collaborator_email]
                    time_zone = collaborated_user.settings.timezone
                    is_unsub = is_unsubscription(
                        collaborator_email, APP.EVNT_CA_EVENT)
                    if not is_unsub:
                        # content for collaborators
                        subject, body, attachment, html, collaborator_name =\
                            content_getter.get_collaborator_content(
                                collaborator_name, cae, cae_slot, time_zone)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body,
                            html=html, attachment=attachment, 
                            smtp_settings=smtp_settings)
                    result = True
            """
            # send emails to slot inquirers
            slot_inquirer_user = User.query.filter_by(
                row_id=inquirer_id).first()
            slot_inquirer_email = slot_inquirer_user.email
            slot_inquirer_name = slot_inquirer_user.profile.first_name
            to_addresses = [slot_inquirer_email]
            time_zone = slot_inquirer_user.settings.timezone or\
                current_app.config['USER_DEFAULT_TIMEZONE']
            is_unsub = is_unsubscription(
                slot_inquirer_email, APP.EVNT_CA_EVENT)
            if not is_unsub:
                # content for collaborators
                subject, body, attachment, html, slot_inquirer_name =\
                    content_getter.get_slot_inquirer_content(
                        slot_inquirer_name, cae, cae_slot, time_zone,
                        slot_inquirer_email)
                send_email_actual(
                    subject=subject, from_name=from_name,
                    keywords=APP.CORPORATE_EMAIL_TASK,
                    from_email=from_email, to_addresses=to_addresses,
                    reply_to=reply_to, cc_addresses=cc_emails, body=body,
                    html=html, attachment=attachment,
                    smtp_settings=smtp_settings)
            result = True
            # we are not sending an email to the participant on
            # slot inquiry confirmation for now
            """
            # send emails to participants
            # # TODO: maybe send to the participants only who are assigned
            # to the given slot
            participants = CorporateAccessEventParticipant.query.filter_by(
                corporate_access_event_id=cae_id).all()
            if participants:
                for participant in participants:
                    if participant.participant_id:
                        participant_user = User.query.filter_by(
                            row_id=participant.participant_id).first()
                        participant_email = participant_user.email
                        participant_name = participant_user.profile.first_name
                        time_zone = participant_user.settings.timezone
                    else:
                        participant_email = participant.participant_email
                        participant_name = participant.participant_first_name
                    to_addresses = [participant_email]
                    is_unsub = is_unsubscription(
                        participant_email, APP.EVNT_CA_EVENT)
                    if not is_unsub:
                        # content for participants
                        subject, body, attachment, html, participant_name =\
                            content_getter.get_participant_content(
                                participant_name, cae, cae_slot, time_zone)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body,
                            html=html, attachment=attachment, 
                            smtp_settings=smtp_settings)
                    result = True
            """
        except Exception as e:
            raise e
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def send_corporate_access_event_slot_inquiry_deletion_email(
        self, result, cae_id, creator_email, creator_name,
        collaborator_ids, inquirer_id, *args, **kwargs):
    """
    Sends the corporate access event slot inquiry deletion email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param cae_slot_id:
        the row id of the corporate_access_event_slot for which email is to be
        generated
    :param cae_id:
        the row id of the corporate_access_event for which email is to be
        generated
    :param inquirer_id:
        the created_by value of inquirer i.e. invitee_id
    """
    if result:
        try:
            cae = CorporateAccessEvent.query.get(cae_id)
            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            # initialize
            content_getter = SlotInquiryDeletionContent(cae)
            subject = ''
            html = ''
            attachment = ''
            body = ''
            # cc email list
            cc_emails = []
            if cae.cc_emails:
                cc_emails = list(set(cae.cc_emails))
            # generate event url for login or registration
            # event_url = generate_event_book_email_link(
            #     current_app.config['CORPACCS_EVENT_JOIN_ADD_URL'], cae_id)

            smtp_settings = get_smtp_settings(cae.created_by)
            # first send to creator
            creator_email = creator_email
            creator_name = creator_name
            to_addresses = [creator_email]
            is_unsub = is_unsubscription(
                creator_email, APP.EVNT_CA_EVENT)
            if not is_unsub:
                # content for creator
                subject, body, attachment, html, creator_name = content_getter.\
                    get_creator_content(creator_name, cae, creator_email)
                send_email_actual(
                    subject=subject, keywords=APP.CORPORATE_EMAIL_TASK,
                    from_name=from_name, from_email=from_email,
                    to_addresses=to_addresses, cc_addresses=cc_emails,
                    reply_to=reply_to, body=body,
                    html=html, attachment=attachment,
                    smtp_settings=smtp_settings)
            result = True

            # send emails to collaborators
            if collaborator_ids:
                for collaborator_id in collaborator_ids:
                    collaborated_user = User.query.filter_by(
                        row_id=collaborator_id).first()
                    collaborator_email = collaborated_user.email
                    collaborator_name =\
                        collaborated_user.profile.first_name
                    to_addresses = [collaborator_email]
                    is_unsub = is_unsubscription(
                        collaborator_email, APP.EVNT_CA_EVENT)
                    if not is_unsub:
                        # content for collaborators
                        subject, body, attachment, html, collaborator_name =\
                            content_getter.get_collaborator_content(
                                collaborator_name, cae, collaborator_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, cc_addresses=cc_emails,
                            body=body, html=html, attachment=attachment,
                            smtp_settings=smtp_settings)
                    result = True

            # send emails to slot inquirers
            slot_inquirer_user = User.query.filter_by(
                row_id=inquirer_id).first()
            slot_inquirer_email = slot_inquirer_user.email
            slot_inquirer_name = slot_inquirer_user.profile.first_name
            to_addresses = [slot_inquirer_email]
            is_unsub = is_unsubscription(
                slot_inquirer_email, APP.EVNT_CA_EVENT)
            if not is_unsub:
                # content for collaborators
                subject, body, attachment, html, slot_inquirer_name =\
                    content_getter.get_slot_inquirer_content(
                        slot_inquirer_name, cae, slot_inquirer_email)
                send_email_actual(
                    subject=subject, from_name=from_name,
                    keywords=APP.CORPORATE_EMAIL_TASK,
                    from_email=from_email, to_addresses=to_addresses,
                    reply_to=reply_to, body=body,
                    html=html, attachment=attachment,
                    smtp_settings=smtp_settings)
            result = True

            # send emails to participants
            # # TODO: maybe send to the participants only who are assinged
            # to the given slot
            participants = CorporateAccessEventParticipant.query.filter_by(
                corporate_access_event_id=cae_id).all()
            if participants:
                for participant in participants:
                    if participant.participant_id:
                        # if participant is the creator do not
                        # send email again to creator
                        if participant.participant_id == cae.creator.row_id:
                            continue
                        participant_user = User.query.filter_by(
                            row_id=participant.participant_id).first()
                        participant_email = participant_user.email
                        participant_name = participant_user.profile.first_name
                    else:
                        participant_email = participant.participant_email
                        participant_name = participant.participant_first_name
                    to_addresses = [participant_email]
                    is_unsub = is_unsubscription(
                        participant_email, APP.EVNT_CA_EVENT)

                    if not is_unsub :
                        # content for participants
                        subject, body, attachment, html, participant_name =\
                            content_getter.get_participant_content(
                                participant_name, cae, participant_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, cc_addresses=cc_emails, body=body,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings)
                    result = True

        except Exception as e:
            raise e
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def send_corporate_access_event_invitee_updated_email(
        self, result, row_id, invitee_list, *args, **kwargs):
    """
    Sends the corporate access event updated invitee email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the corporate_access_event for which email is to be
        generated
    """

    if result:
        try:
            cae = CorporateAccessEvent.query.get(row_id)
            if cae is None:
                logger.exception('Corporate Access Event does not exist')
                return False
            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            # initialize
            content_getter = EventUpdateContent(cae)
            subject = ''
            html = ''
            attachment = ''
            body = ''
            # cc email list
            cc_emails = []
            if cae.cc_emails:
                cc_emails = list(set(cae.cc_emails))
            smtp_settings = get_smtp_settings(cae.created_by)
            # send emails to invitees
            invitees = CorporateAccessEventInvitee.query.filter_by(
                corporate_access_event_id=row_id).all()
            if invitees:
                for invitee in invitees:
                    if invitee.invitee_email not in invitee_list:
                        continue
                    invitee_email = invitee.invitee_email
                    invitee_name = invitee.invitee_first_name
                    time_zone = cae.creator.settings.timezone or\
                        current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [invitee_email]
                    is_unsub = is_unsubscription(
                        invitee_email, APP.EVNT_CA_EVENT)
                    if not is_unsub:
                        # content for invitee
                        subject, body, attachment, html, invitee_name =\
                            content_getter.get_invitee_content(
                                invitee_name, cae, time_zone, invitee,
                                invitee_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, cc_addresses=cc_emails, body=body,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings)
                    result = True

        except Exception as e:
            raise e
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def send_corporate_access_event_cancellation_email(
        self, result, row_id, *args, **kwargs):
    """
    Sends the corporate access event cancellation email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the corporate_access_event for which email is to be
        generated
    """

    if result:
        try:
            cae = CorporateAccessEvent.query.get(row_id)
            if cae is None:
                logger.exception('Corporate Access Event does not exist')
                return False
            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            # initialize
            content_getter = CancellationContent(cae)
            subject = ''
            html = ''
            attachment = ''
            body = ''
            # cc email list
            cc_emails = []
            if cae.cc_emails:
                cc_emails = list(set(cae.cc_emails))
            smtp_settings = get_smtp_settings(cae.created_by)
            # send emails to invitees
            invitees = CorporateAccessEventInvitee.query.filter_by(
                corporate_access_event_id=row_id).all()
            if invitees:
                for invitee in invitees:
                    if invitee.invitee_id:
                        invited_user = User.query.filter_by(
                            row_id=invitee.invitee_id).first()
                        invitee_email = invited_user.email
                        invitee_name = invited_user.profile.first_name
                        time_zone = invited_user.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    else:
                        invitee_email = invitee.invitee_email
                        invitee_name = invitee.invitee_first_name
                        time_zone = cae.creator.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [invitee_email]
                    is_unsub = is_unsubscription(
                        invitee_email, APP.EVNT_CA_EVENT)
                    if not is_unsub:
                        # content for invitee
                        subject, body, attachment, html, invitee_name =\
                            content_getter.get_invitee_content(
                                invitee_name, cae, time_zone, invitee,
                                invitee_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.CORPORATE_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, cc_addresses=cc_emails, body=body,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings)
                    result = True

        except Exception as e:
            raise e
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def send_corporate_access_event_register_email(
        self, result, row_id, invitee_row_id, *args, **kwargs):
    """
    Sends the ca event register email to invitee

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the ca event invitee
    """

    if result:
        try:
            cae = CorporateAccessEvent.query.get(row_id)
            if cae is None:
                logger.exception('Corporate Access Event does not exist')
                return False
            location = ""
            if cae.city:
                location += cae.city + " "
            if cae.state:
                location += cae.state + " "
            if cae.country:
                location += cae.country
            ics_param = {
                "summery": cae.title,
                "category": cae.event_sub_type.name,
                "dtstart": cae.started_at,
                "dtend": cae.ended_at,
                "description": cae.description,
                "location": location}
            ics_file = generate_ics_file(**ics_param)
            # generate the email content
            # default sender details
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            # get the sender details, incase it is set in account_settings
            acc_setts = cae.account.settings  # account settings
            if (acc_setts.event_sender_email and
                    acc_setts.event_sender_name and acc_setts.verified_status):
                # #TODO: always reverify, before sending
                """
                verify_result = verify_email(acc_setts, reverify=True)
                acc_setts = verify_result['account_settings']"""
                if acc_setts.verified_status:
                    from_name = acc_setts.event_sender_name
                    from_email = acc_setts.event_sender_email
                """else:
                    logger.exception(verify_result['extra_message'])
                db.session.add(acc_setts)
                db.session.commit()"""
            # when creator want to send mail to CAEvent supporter
            reply_to = ''

            # initialize
            content_getter = LaunchContent(cae)
            subject = ''
            html = ''
            attachment = ''
            body = ''
            # cc email list
            cc_emails = []
            if cae.cc_emails:
                cc_emails = list(set(cae.cc_emails))
            smtp_settings = get_smtp_settings(cae.created_by)
            # send emails to invitees
            invitee = CorporateAccessEventInvitee.query.filter_by(
                row_id=invitee_row_id).first()
            if invitee.invitee_id:
                invited_user = User.query.filter_by(
                    row_id=invitee.invitee_id).first()
                invitee_email = invited_user.email
                invitee_name = invited_user.profile.first_name + ' ' + invited_user.profile.last_name
                time_zone = invited_user.settings.timezone or \
                    current_app.config['USER_DEFAULT_TIMEZONE']
            else:
                invitee_email = invitee.invitee_email
                invitee_name = invitee.invitee_first_name + ' ' + invitee.invitee_last_name
                time_zone = cae.creator.settings.timezone or \
                    current_app.config['USER_DEFAULT_TIMEZONE']
            to_addresses = [invitee_email]
            is_unsub = is_unsubscription(
                invitee_email, APP.EVNT_CA_EVENT)
            if not is_unsub:
                # content for invitee
                subject, body, attachment, html, invitee_name = \
                    content_getter.get_register_invitee_content(
                        invitee_name, cae, time_zone, invitee, invitee_email)
                send_email_actual(
                    subject=subject, from_name=from_name,
                    keywords=APP.CORPORATE_EMAIL_TASK,
                    from_email=from_email, to_addresses=to_addresses,
                    reply_to=reply_to, cc_addresses=cc_emails, body=body,
                    html=html, attachment=attachment,
                    smtp_settings=smtp_settings, ics_file=ics_file)
                invitee.email_status = APP.EMAIL_SENT
                invitee.is_mail_sent = True
                db.session.add(invitee)
                db.session.commit()
            result = True
            if content_getter.attachment:
                delete_fs_file(content_getter.attachment)
            shutil.rmtree(os.path.dirname(ics_file))
        except Exception as e:
            raise e
            logger.exception(e)
            result = False

        return result
