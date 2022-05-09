"""
webinar related email tasks, for each type of email
"""
import os
import shutil

from flask import current_app

from app.base import constants as APP
from app.webinar_resources.webinars.models import Webinar
from app.webinar_resources.webinar_hosts.models import WebinarHost
from app.webinar_resources.webinar_invitees.models import WebinarInvitee
from app.webinar_resources.webinar_participants.models import (
    WebinarParticipant)
from app.webinar_resources.webinar_rsvps.models import WebinarRSVP
from app.webinar_resources.webinar_attendees.models import WebinarAttendee
from app.resources.users.models import User
from app.common.helpers import generate_event_book_email_link
from app import db
from app.resources.email_credentials.helpers import get_smtp_settings
from app.common.helpers import generate_ics_file

from queueapp.tasks import celery_app, logger, send_email_actual
from queueapp.webinars.email_contents import (
    LaunchContent, CompletionContent, UpdateContent, RegisterContent,
    CancellationContent, ReminderContent)
from app.resources.unsubscriptions.helpers import is_unsubscription


@celery_app.task(bind=True, ignore_result=True)
def send_webinar_launch_email(self, result, row_id, *args, **kwargs):
    """
    Sends the webinar related email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the webinar for which email is to be generated
    """
    if result:
        try:
            webinar = Webinar.query.get(row_id)
            if webinar is None:
                logger.exception('Webinar does not exist')
                return False
            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            smtp_settings = get_smtp_settings(webinar.created_by)
            # initialize
            content_getter = LaunchContent(webinar)
            time_zone = webinar.creator.settings.timezone or\
                current_app.config['USER_DEFAULT_TIMEZONE']
            if webinar.open_to_public:
                event_url = generate_event_book_email_link(
                    current_app.config['WEBINAR_PUBLIC_EVENT_JOIN_ADD_URL'],
                    webinar, event_type=APP.EVNT_PUBLIC_WEBINAR)
            else:
                event_url = generate_event_book_email_link(
                    current_app.config['WEBINAR_EVENT_JOIN_ADD_URL'],
                    webinar)
            ics_param = {
                "summery": webinar.title,
                "dtstart": webinar.started_at,
                "dtend": webinar.ended_at,
                "description": webinar.description + '\n' + event_url}
            ics_file = generate_ics_file(**ics_param)
            # cc email list
            cc_emails = []
            if webinar.cc_emails:
                cc_emails = list(set(webinar.cc_emails))
            if not webinar.creator_mail_sent :
                # first send to creator
                creator_name = webinar.creator.profile.first_name
                time_zone = webinar.creator.settings.timezone
                to_addresses = [webinar.creator.email]
                is_unsub = is_unsubscription(to_addresses[0], APP.EVNT_WEBINAR)
                if not is_unsub:
                    # content for creator
                    subject, body, attachment, html, creator_name = content_getter.\
                        get_creator_content(
                            creator_name, webinar, time_zone, to_addresses[0],
                            event_url)
                    send_email_actual(
                        subject=subject, keywords=APP.WEBINAR,
                        from_name=from_name, from_email=from_email,
                        to_addresses=to_addresses, reply_to=reply_to, body=body,
                        cc_addresses=cc_emails, html=html,
                        attachment=attachment, smtp_settings=smtp_settings,
                        ics_file=ics_file)
                    result = True
            # send emails to invitees
            invitees = WebinarInvitee.query.filter_by(
                webinar_id=row_id, email_status=APP.EMAIL_NOT_SENT).all()
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
                        time_zone = webinar.creator.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [invitee_email]
                    is_unsub = is_unsubscription(invitee_email,
                        APP.EVNT_WEBINAR, invitee)
                    if not is_unsub:
                        subject, body, attachment, html, invitee_name = content_getter.\
                            get_invitee_content(
                                invitee_name, webinar, time_zone, event_url,
                                invitee_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBINAR,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body, cc_addresses=cc_emails,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)

                        invitee.email_status = APP.EMAIL_SENT
                        invitee.is_mail_sent = True
                        db.session.add(invitee)
                        db.session.commit()
                        result = True
            # send emails to participants
            participants = WebinarParticipant.query.filter_by(
                webinar_id=row_id, email_status=APP.EMAIL_NOT_SENT).all()
            if participants:
                for participant in participants:
                    if participant.participant_id:
                        participant_user = User.query.filter_by(
                            row_id=participant.participant_id).first()
                        # if participant is the creator do not
                        # send email again to creator
                        if participant.participant_id == \
                                webinar.creator.row_id:
                            continue
                        participant_email = participant_user.email
                        participant_name = participant_user.profile.first_name
                        time_zone = participant_user.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    else:
                        participant_email = participant.participant_email
                        participant_name = participant.participant_first_name
                        time_zone = webinar.creator.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [participant_email]
                    is_unsub = is_unsubscription(participant_email,
                        APP.EVNT_WEBINAR, participant)
                    if not is_unsub:
                        subject, body, attachment, html, participant_name = \
                            content_getter.get_participant_content(
                                participant_name, webinar, time_zone,
                                participant_email, event_url)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBINAR,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body, cc_addresses=cc_emails,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)

                        participant.email_status = APP.EMAIL_SENT
                        participant.is_mail_sent = True
                        db.session.add(participant)
                        db.session.commit()
                        result = True
            # send emails to hosts
            hosts = WebinarHost.query.filter_by(
                webinar_id=row_id, email_status = APP.EMAIL_NOT_SENT).all()
            if hosts:
                for host in hosts:
                    if host.host_id:
                        host_user = User.query.filter_by(
                            row_id=host.host_id).first()
                        # if host is the creator do not
                        # send email again to creator
                        if host.host_id == webinar.creator.row_id:
                            continue
                        host_email = host_user.email
                        host_name = host_user.profile.first_name
                        time_zone = host_user.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    else:
                        host_email = host.host_email
                        host_name = host.host_first_name
                        time_zone = webinar.creator.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [host_email]
                    is_unsub = is_unsubscription(host_email,
                        APP.EVNT_WEBINAR, host)
                    if not is_unsub:
                        # content for hosts
                        subject, body, attachment, html, host_name =\
                            content_getter.get_host_content(
                                host_name, webinar, time_zone, host_email,
                                event_url)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBINAR,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body, cc_addresses=cc_emails,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)

                        host.email_status = APP.EMAIL_SENT
                        host.is_mail_sent = True
                        db.session.add(host)
                        db.session.commit()
                        result = True
            # send emails to rsvps
            rsvps = WebinarRSVP.query.filter_by(
                webinar_id=row_id, email_status=APP.EMAIL_NOT_SENT).all()
            if rsvps:
                for rsvp in rsvps:
                    rsvp_email = rsvp.email
                    # if rsvp is the creator do not send email again to creator
                    if rsvp_email == webinar.creator.email:
                        continue
                    to_addresses = [rsvp_email]
                    rsvp_name = rsvp.contact_person
                    is_unsub = is_unsubscription(rsvp_email,
                        APP.EVNT_WEBINAR, rsvp)
                    if not is_unsub:
                        # content for rsvps
                        subject, body, attachment, html, rsvp_name =\
                            content_getter.get_rsvp_content(
                                rsvp_name, webinar, time_zone, rsvp_email,
                                event_url)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBINAR,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body, cc_addresses=cc_emails,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)

                        rsvp.email_status = APP.EMAIL_SENT
                        rsvp.is_mail_sent = True
                        db.session.add(rsvp)
                        db.session.commit()
                        result = True
            shutil.rmtree(os.path.dirname(ics_file))
        except Exception as e:
            raise e
            logger.exception(e)
            result = False

        finally:
            webinar.is_in_process = False
            db.session.add(webinar)
            db.session.commit()

    return result


@celery_app.task(bind=True, ignore_result=True)
def send_webinar_event_new_invitee_email(
        self, result, row_id, invitee_list, invitee_ids, *args, **kwargs):
    """
    Sends the webinar new invitee email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the corporate_access_event for which email is to be
        generated
    """

    if result:
        try:
            webinar = Webinar.query.get(row_id)
            if webinar is None:
                logger.exception('Webinar does not exist')
                return False

            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            smtp_settings = get_smtp_settings(webinar.created_by)
            # initialize
            content_getter = LaunchContent(webinar)
            if webinar.open_to_public:
                event_url = generate_event_book_email_link(
                    current_app.config['WEBINAR_PUBLIC_EVENT_JOIN_ADD_URL'],
                    webinar, event_type=APP.EVNT_PUBLIC_WEBINAR)
            else:
                event_url = generate_event_book_email_link(
                    current_app.config['WEBINAR_EVENT_JOIN_ADD_URL'],
                    webinar)
            ics_param = {
                "summery": webinar.title,
                "dtstart": webinar.started_at,
                "dtend": webinar.ended_at,
                "description": webinar.description + '\n' + event_url}
            ics_file = generate_ics_file(**ics_param)
            # cc email list
            cc_emails = []
            if webinar.cc_emails:
                cc_emails = list(set(webinar.cc_emails))

            # send emails to invitees
            invitees = WebinarInvitee.query.filter_by(
                webinar_id=row_id).all()
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
                        time_zone = webinar.creator.settings.timezone or \
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [invitee_email]
                    is_unsub = is_unsubscription(invitee_email,
                        APP.EVNT_WEBINAR, invitee)
                    if not is_unsub:
                        subject, body, attachment, html, invitee_name = content_getter.\
                            get_invitee_content(invitee_name, webinar, time_zone,
                                                event_url, invitee_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBINAR,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body, cc_addresses=cc_emails,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)
                        invitee.email_status = APP.EMAIL_SENT
                        invitee.is_mail_sent = True
                        db.session.add(invitee)
                        db.session.commit()
                shutil.rmtree(os.path.dirname(ics_file))
                result = True

        except Exception as e:
            raise e
            logger.exception(e)
            result = False

        finally:
            webinar.is_in_process = False
            db.session.add(webinar)
            db.session.commit()

        return result


@celery_app.task(bind=True, ignore_result=True)
def send_webinar_completion_email(self, result, row_id, *args, **kwargs):
    """
    Sends the webinar completion related email.

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the webinar row id
    """
    if result:
        try:
            webinar = Webinar.query.get(row_id)
            if webinar is None:
                logger.exception('Webinar does not exist')
                return False
            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            smtp_settings = get_smtp_settings(webinar.created_by)
            # initialize
            content_getter = CompletionContent(webinar)
            # cc email list
            cc_emails = []
            if webinar.cc_emails:
                cc_emails = list(set(webinar.cc_emails))
            # send emails to participants
            participants = WebinarParticipant.query.filter_by(
                webinar_id=row_id).all()
            if participants:
                for participant in participants:
                    if participant.participant_id:
                        participant_user = User.query.filter_by(
                            row_id=participant.participant_id).first()
                        # if participant is the creator do not
                        # send email again to creator
                        if participant.participant_id == \
                                webinar.creator.row_id:
                            continue
                        participant_email = participant_user.email
                        participant_name = participant_user.profile.first_name
                    else:
                        participant_email = participant.participant_email
                        participant_name = participant.participant_first_name
                    to_addresses = [participant_email]
                    is_unsub = is_unsubscription(participant_email,
                        APP.EVNT_WEBINAR)
                    if not is_unsub:
                        subject, body, attachment, html, participant_name = \
                            content_getter.get_participant_content(
                                participant_name, webinar, participant_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBINAR,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body, cc_addresses=cc_emails,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings)
                        result = True
            # send emails to attendee
            attendees = WebinarAttendee.query.filter_by(
                webinar_id=row_id).all()
            if attendees:
                for attendee in attendees:
                    if attendee.attendee_id:
                        attendee_email = attendee.attendee.email
                        attendee_name = attendee.attendee.profile.first_name
                    to_addresses = [attendee_email]
                    is_unsub = is_unsubscription(attendee_email,
                        APP.EVNT_WEBINAR)
                    if not is_unsub:
                        subject, body, attachment, html, attendee_name =\
                            content_getter.get_attendee_content(
                                attendee_name, webinar, attendee_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBINAR,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body, cc_addresses=cc_emails,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings)
                        result = True
        except Exception as e:
            raise e
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def send_webinar_update_email(self, result, row_id, new_emails,
                              new_invitee_ids, rescheduled, *args, **kwargs):
    """
    Sends the webinar update email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the webinar for which email is to be generated
    """
    if result:
        try:
            webinar = Webinar.query.get(row_id)
            if webinar is None:
                logger.exception('Webinar does not exist')
                return False
            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            smtp_settings = get_smtp_settings(webinar.created_by)
            # initialize
            content_getter = UpdateContent(webinar, rescheduled)
            event_url = generate_event_book_email_link(
                current_app.config['WEBINAR_EVENT_JOIN_ADD_URL'],
                webinar)
            ics_param = {
                "summery": webinar.title,
                "dtstart": webinar.started_at,
                "dtend": webinar.ended_at,
                "description": webinar.description + '\n' + event_url}
            ics_file = generate_ics_file(**ics_param)
            # cc email list
            cc_emails = []
            if webinar.cc_emails:
                cc_emails = list(set(webinar.cc_emails))
            # first send to creator
            creator_name = webinar.creator.profile.first_name
            to_addresses = [webinar.creator.email]
            time_zone = webinar.creator.settings.timezone or\
                current_app.config['USER_DEFAULT_TIMEZONE']
            is_unsub = is_unsubscription(to_addresses[0], APP.EVNT_WEBINAR)
            if not is_unsub:
                # content for creator
                subject, body, attachment, html, creator_name = content_getter.\
                    get_creator_content(
                        creator_name, webinar, time_zone, to_addresses[0],
                        event_url)
                send_email_actual(
                    subject=subject, keywords=APP.WEBINAR,
                    from_name=from_name, from_email=from_email,
                    to_addresses=to_addresses, reply_to=reply_to, body=body,
                    html=html, attachment=attachment,
                    smtp_settings=smtp_settings, ics_file=ics_file)
                result = True
            # send emails to invitees
            invitees = WebinarInvitee.query.filter_by(webinar_id=row_id).all()
            if invitees:
                for invitee in invitees:
                    if invitee.invitee_id:
                        if invitee.invitee_id in new_invitee_ids:
                            continue
                        invited_user = User.query.filter_by(
                            row_id=invitee.invitee_id).first()
                        invitee_email = invited_user.email
                        invitee_name = invited_user.profile.first_name
                        time_zone = invited_user.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    else:
                        invitee_email = invitee.invitee_email
                        if invitee_email in new_emails:
                            continue
                        invitee_name = invitee.invitee_first_name
                        time_zone = webinar.creator.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [invitee_email]
                    is_unsub = is_unsubscription(invitee_email,
                        APP.EVNT_WEBINAR)
                    if not is_unsub:
                        subject, body, attachment, html, invitee_name = content_getter.\
                            get_invitee_content(
                                invitee_name, webinar, time_zone, event_url,
                                invitee_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBINAR,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body, cc_addresses=cc_emails,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)
                        result = True
            # send emails to participants
            participants = WebinarParticipant.query.filter_by(
                webinar_id=row_id).all()
            if participants:
                for participant in participants:
                    if participant.participant_id:
                        participant_user = User.query.filter_by(
                            row_id=participant.participant_id).first()
                        # if participant is the creator do not
                        # send email again to creator
                        if participant.participant_id == \
                                webinar.creator.row_id:
                            continue
                        participant_email = participant_user.email
                        participant_name = participant_user.profile.first_name
                        time_zone = participant_user.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    else:
                        participant_email = participant.participant_email
                        participant_name = participant.participant_first_name
                        time_zone = webinar.creator.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [participant_email]
                    is_unsub = is_unsubscription(participant_email,
                        APP.EVNT_WEBINAR)
                    if not is_unsub:
                        subject, body, attachment, html, participant_name = \
                            content_getter.get_participant_content(
                                participant_name, webinar, time_zone,
                                participant_email, event_url)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBINAR,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body, cc_addresses=cc_emails,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)
                        result = True
            # send emails to hosts
            hosts = WebinarHost.query.filter_by(webinar_id=row_id).all()
            if hosts:
                for host in hosts:
                    if host.host_id:
                        host_user = User.query.filter_by(
                            row_id=host.host_id).first()
                        # if host is the creator do not
                        # send email again to creator
                        if host.host_id == webinar.creator.row_id:
                            continue
                        host_email = host_user.email
                        host_name = host_user.profile.first_name
                        time_zone = host_user.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    else:
                        host_email = host.host_email
                        host_name = host.host_first_name
                        time_zone = webinar.creator.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [host_email]
                    is_unsub = is_unsubscription(host_email,
                        APP.EVNT_WEBINAR)
                    if not is_unsub:
                        # content for hosts
                        subject, body, attachment, html, host_name =\
                            content_getter.get_host_content(
                                host_name, webinar, time_zone, host_email,
                                event_url)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBINAR,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body, cc_addresses=cc_emails,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)
                        result = True
            # send emails to rsvps
            rsvps = WebinarRSVP.query.filter_by(webinar_id=row_id).all()
            if rsvps:
                for rsvp in rsvps:
                    rsvp_email = rsvp.email
                    # if rsvp is the creator do not send email again to creator
                    if rsvp_email == webinar.creator.email:
                        continue
                    to_addresses = [rsvp_email]
                    rsvp_name = rsvp.contact_person
                    is_unsub = is_unsubscription(rsvp_email,
                        APP.EVNT_WEBINAR)
                    if not is_unsub:
                        # content for rsvps
                        subject, body, attachment, html, rsvp_name =\
                            content_getter.get_rsvp_content(
                                rsvp_name, webinar, time_zone, rsvp_email,
                                event_url)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBINAR,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body, cc_addresses=cc_emails,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)
                        result = True
            shutil.rmtree(os.path.dirname(ics_file))
        except Exception as e:
            raise e
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def send_webinar_register_email(self, result, row_id, *args, **kwargs):
    """
    Sends the webinar register email to invitee

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the webinar invitee
    """
    if result:
        try:
            invitee = WebinarInvitee.query.get(row_id)
            if invitee is None:
                logger.exception('Webinar Invitee does not exist')
                return False
            ics_param = {
                "summery": invitee.webinar.title,
                "dtstart": invitee.webinar.started_at,
                "dtend": invitee.webinar.ended_at,
                "description": invitee.webinar.description}
            ics_file = generate_ics_file(**ics_param)
            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            smtp_settings = get_smtp_settings(invitee.webinar.created_by)
            # initialize
            content_getter = RegisterContent(invitee.webinar)
            # cc email list
            cc_emails = []
            # for bigmarker conference_url
            conference_url = ''
            if invitee.webinar.cc_emails:
                cc_emails = list(set(invitee.webinar.cc_emails))
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
                time_zone = invitee.webinar.creator.settings.timezone or\
                    current_app.config['USER_DEFAULT_TIMEZONE']
            conference_url = invitee.conference_url
            to_addresses = [invitee_email]
            is_unsub = is_unsubscription(invitee_email,
                APP.EVNT_WEBINAR)
            if not is_unsub:
                subject, body, attachment, html, invitee_name = content_getter.\
                    get_invitee_content(
                        invitee_name, invitee.webinar, time_zone,
                        conference_url, invitee_email)
                send_email_actual(
                    subject=subject, from_name=from_name,
                    keywords=APP.WEBINAR,
                    from_email=from_email, to_addresses=to_addresses,
                    reply_to=reply_to, body=body, cc_addresses=cc_emails,
                    html=html, attachment=attachment,
                    smtp_settings=smtp_settings, ics_file=ics_file)
                result = True
            shutil.rmtree(os.path.dirname(ics_file))
        except Exception as e:
            raise e
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def send_webinar_cancellation_email(self, result, row_id, *args, **kwargs):
    """
    Sends the webinar cancellation email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the webinar for which email is to be generated
    """
    if result:
        try:
            webinar = Webinar.query.get(row_id)
            if webinar is None:
                logger.exception('Webinar does not exist')
                return False
            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            smtp_settings = get_smtp_settings(webinar.created_by)
            # initialize
            content_getter = CancellationContent(webinar)
            event_url = generate_event_book_email_link(
                current_app.config['WEBINAR_EVENT_JOIN_ADD_URL'],
                webinar)
            # cc email list
            cc_emails = []
            if webinar.cc_emails:
                cc_emails = list(set(webinar.cc_emails))
            # send emails to invitees
            invitees = WebinarInvitee.query.filter_by(webinar_id=row_id).all()
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
                        time_zone = webinar.creator.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [invitee_email]
                    is_unsub = is_unsubscription(invitee_email,
                        APP.EVNT_WEBINAR)
                    if not is_unsub:
                        subject, body, attachment, html, invitee_name = content_getter.\
                            get_invitee_content(
                                invitee_name, webinar, time_zone, event_url,
                                invitee_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBINAR,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body, cc_addresses=cc_emails,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings)
                        result = True
        except Exception as e:
            raise e
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def send_webinar_reminder_email(self, result, row_id, *args, **kwargs):
    """
    Sends the webinar reminder email

    :param result:
        the result of previous task when chaining. Remember to pass True,
        when called as first of chain, or individually.
    :param row_id:
        the row id of the webinar for which email is to be generated
    """
    if result:
        try:
            webinar = Webinar.query.get(row_id)
            if webinar is None:
                logger.exception('Webinar does not exist')
                return False
            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            smtp_settings = get_smtp_settings(webinar.created_by)
            # initialize
            content_getter = ReminderContent(webinar)

            time_zone = webinar.creator.settings.timezone or \
                current_app.config['USER_DEFAULT_TIMEZONE']

            if webinar.open_to_public:
                event_url = generate_event_book_email_link(
                    current_app.config['WEBINAR_PUBLIC_EVENT_JOIN_ADD_URL'],
                    webinar, event_type=APP.EVNT_PUBLIC_WEBINAR)
            else:
                event_url = generate_event_book_email_link(
                    current_app.config['WEBINAR_EVENT_JOIN_ADD_URL'],
                    webinar)
            ics_param = {
                "summery": webinar.title,
                "dtstart": webinar.started_at,
                "dtend": webinar.ended_at,
                "description": webinar.description + '\n' + event_url}
            ics_file = generate_ics_file(**ics_param)
            # cc email list
            cc_emails = []
            if webinar.cc_emails:
                cc_emails = list(set(webinar.cc_emails))
            # first send to creator
            creator_name = webinar.creator.profile.first_name
            time_zone = webinar.creator.settings.timezone
            to_addresses = [webinar.creator.email]
            is_unsub = is_unsubscription(to_addresses[0],
                APP.EVNT_WEBINAR)
            if not is_unsub:
                # content for creator
                subject, body, attachment, html, creator_name = content_getter. \
                    get_invitee_content(
                        creator_name, webinar, time_zone,
                        webinar.presenter_url,None ,to_addresses[0])
                send_email_actual(
                    subject=subject, keywords=APP.WEBINAR,
                    from_name=from_name, from_email=from_email,
                    to_addresses=to_addresses, reply_to=reply_to,
                    cc_addresses=cc_emails, body=body, html=html,
                    attachment=attachment, smtp_settings=smtp_settings,
                    ics_file=ics_file)
                result = True
            # send emails to invitees
            invitees = WebinarInvitee.query.filter_by(webinar_id=row_id).all()
            if invitees:
                for invitee in invitees:
                    if invitee.invitee_id:
                        invited_user = User.query.filter_by(
                            row_id=invitee.invitee_id).first()
                        invitee_email = invited_user.email
                        invitee_name = invited_user.profile.first_name
                        time_zone = invited_user.settings.timezone or \
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    else:
                        invitee_email = invitee.invitee_email
                        invitee_name = invitee.invitee_first_name
                        time_zone = webinar.creator.settings.timezone or \
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [invitee_email]
                    is_unsub = is_unsubscription(invitee_email,
                        APP.EVNT_WEBINAR)
                    if not is_unsub:
                        subject, body, attachment, html, invitee_name = content_getter. \
                            get_invitee_content(invitee_name, webinar, time_zone,
                                invitee.conference_url, event_url, invitee_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBINAR,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body, html=html,
                            attachment=attachment, smtp_settings=smtp_settings,
                            ics_file=ics_file)
                        result = True
            # send emails to participants
            participants = WebinarParticipant.query.filter_by(
                webinar_id=row_id).all()
            if participants:
                for participant in participants:
                    if participant.participant_id:
                        participant_user = User.query.filter_by(
                            row_id=participant.participant_id).first()
                        # if participant is the creator do not
                        # send email again to creator
                        if participant.participant_id == \
                                webinar.creator.row_id:
                            continue
                        participant_email = participant_user.email
                        participant_name = participant_user.profile.first_name
                        time_zone = participant_user.settings.timezone or \
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    else:
                        participant_email = participant.participant_email
                        participant_name = participant.participant_first_name
                        time_zone = webinar.creator.settings.timezone or \
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [participant_email]
                    is_unsub = is_unsubscription(participant_email,
                        APP.EVNT_WEBINAR)
                    if not is_unsub:
                        subject, body, attachment, html, participant_name = \
                            content_getter.get_invitee_content(
                                participant_name, webinar, time_zone,
                                participant.conference_url, None,
                                participant_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBINAR,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body, cc_addresses=cc_emails,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)
                        result = True
            # send emails to hosts
            hosts = WebinarHost.query.filter_by(webinar_id=row_id).all()
            if hosts:
                for host in hosts:
                    if host.host_id:
                        host_user = User.query.filter_by(
                            row_id=host.host_id).first()
                        # if host is the creator do not
                        # send email again to creator
                        if host.host_id == webinar.creator.row_id:
                            continue
                        host_email = host_user.email
                        host_name = host_user.profile.first_name
                        time_zone = host_user.settings.timezone or \
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    else:
                        host_email = host.host_email
                        host_name = host.host_first_name
                        time_zone = webinar.creator.settings.timezone or \
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [host_email]
                    is_unsub = is_unsubscription(host_email,
                        APP.EVNT_WEBINAR)
                    if not is_unsub:
                        # content for hosts
                        subject, body, attachment, html, host_name = \
                            content_getter.get_invitee_content(
                                host_name, webinar, time_zone,
                                host.conference_url, None, host_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBINAR,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body, cc_addresses=cc_emails,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)
                        result = True
            # send emails to rsvps
            rsvps = WebinarRSVP.query.filter_by(webinar_id=row_id).all()
            if rsvps:
                for rsvp in rsvps:
                    rsvp_email = rsvp.email
                    # if rsvp is the creator do not send email again to creator
                    if rsvp_email == webinar.creator.email:
                        continue
                    to_addresses = [rsvp_email]
                    rsvp_name = rsvp.contact_person
                    is_unsub = is_unsubscription(rsvp_email,
                        APP.EVNT_WEBINAR)
                    if not is_unsub:
                        # content for rsvps
                        subject, body, attachment, html, rsvp_name = \
                            content_getter.get_invitee_content(
                                rsvp_name, webinar, time_zone,
                                rsvp.conference_url, None, rsvp_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBINAR,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body, cc_addresses=cc_emails,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)
                        result = True
            shutil.rmtree(os.path.dirname(ics_file))
        except Exception as e:
            raise e
            logger.exception(e)
            result = False

    return result


