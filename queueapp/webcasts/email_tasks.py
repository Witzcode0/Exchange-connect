"""
webcast related email tasks
"""
import os
import shutil

from flask import current_app
from app import db

from app.common.helpers import generate_event_book_email_link
from app.webcast_resources.webcasts.models import Webcast
from app.webcast_resources.webcast_hosts.models import WebcastHost
from app.webcast_resources.webcast_invitees.models import WebcastInvitee
from app.webcast_resources.webcast_participants.models import (
    WebcastParticipant)
from app.webcast_resources.webcast_rsvps.models import WebcastRSVP
from app.webcast_resources.webcast_attendees.models import WebcastAttendee
from app.resources.users.models import User
from app.resources.email_credentials.helpers import get_smtp_settings
from app.common.helpers import generate_ics_file

from queueapp.tasks import celery_app, logger, send_email_actual
from queueapp.webcasts.email_contents import (
    LaunchContent, CompletionContent, UpdateContent, CancellationContent)
from app.base import constants as APP
from app.resources.unsubscriptions.helpers import is_unsubscription


@celery_app.task(bind=True, ignore_result=True)
def send_webcast_launch_email(self, result, row_id, *args, **kwargs):
    """
    Sends the webcast related email.

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the webcast row id
    """
    if result:
        try:
            webcast = Webcast.query.get(row_id)
            if webcast is None:
                logger.exception('Webcast does not exist')
                return False
            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            smtp_settings = get_smtp_settings(webcast.created_by)
            event_url = generate_event_book_email_link(
                current_app.config['WEBCAST_EVENT_JOIN_ADD_URL'],
                webcast)
            ics_param = {
                "summery": webcast.title,
                "dtstart": webcast.started_at,
                "dtend": webcast.ended_at,
                "description": webcast.description + '\n' + event_url}
            ics_file = generate_ics_file(**ics_param)
            # initialize
            content_getter = LaunchContent(webcast)
            # cc email list
            cc_emails = []
            if webcast.cc_emails:
                cc_emails = list(set(webcast.cc_emails))
            if not webcast.creator_mail_sent:
                # first send to creator
                creator_name = webcast.creator.profile.first_name
                time_zone = webcast.creator.settings.timezone or\
                    current_app.config['USER_DEFAULT_TIMEZONE']
                to_addresses = [webcast.creator.email]
                is_unsub = is_unsubscription(to_addresses[0],APP.EVNT_WEBCAST)
                if not is_unsub:
                    # content for creator
                    subject, body, attachment, html, creator_name = content_getter.\
                        get_creator_content(creator_name, webcast, time_zone,
                            to_addresses[0])
                    send_email_actual(
                        subject=subject, keywords=APP.WEBCAST,
                        from_name=from_name, from_email=from_email,
                        to_addresses=to_addresses, cc_addresses=cc_emails,
                        reply_to=reply_to, body=body, html=html,
                        attachment=attachment, smtp_settings=smtp_settings,
                        ics_file=ics_file)
                    result = True
            # send emails to invitees
            invitees = WebcastInvitee.query.filter_by(
                webcast_id=row_id, email_status= APP.EMAIL_NOT_SENT).all()
            if invitees:
                for invitee in invitees:
                    if invitee.invitee_id:
                        invited_user = User.query.filter_by(
                            row_id=invitee.invitee_id).first()
                        invitee_email = invited_user.email
                        time_zone = invited_user.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                        invitee_name = invited_user.profile.first_name
                    else:
                        invitee_email = invitee.invitee_email
                        invitee_name = invitee.invitee_first_name
                        time_zone = webcast.creator.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [invitee_email]
                    is_unsub = is_unsubscription(invitee_email,
                        APP.EVNT_WEBCAST, invitee)
                    if not is_unsub:
                        subject, body, attachment, html, invitee_name = content_getter.\
                            get_invitee_content(invitee_name, webcast, time_zone,
                                invitee, invitee_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBCAST,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, cc_addresses=cc_emails, body=body,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)

                        invitee.email_status = APP.EMAIL_SENT
                        invitee.is_mail_sent = True
                        db.session.add(invitee)
                        db.session.commit()
                        result = True
            # send emails to participants
            participants = WebcastParticipant.query.filter_by(
                webcast_id=row_id, email_status= APP.EMAIL_NOT_SENT).all()
            if participants:
                for participant in participants:
                    if participant.participant_id:
                        participant_user = User.query.filter_by(
                            row_id=participant.participant_id).first()
                        # if participant is the creator do not
                        # send email again to creator
                        if participant.participant_id == \
                                webcast.creator.row_id:
                            continue
                        participant_email = participant_user.email
                        participant_name = participant_user.profile.first_name
                        time_zone = participant_user.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    else:
                        participant_email = participant.participant_email
                        participant_name = participant.participant_first_name
                        time_zone = webcast.creator.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [participant_email]
                    is_unsub = is_unsubscription(participant_email,
                        APP.EVNT_WEBCAST, participant)
                    if not is_unsub:
                        subject, body, attachment, html, participant_name = \
                            content_getter.get_participant_content(
                                participant_name, webcast, time_zone,
                                participant_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBCAST,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, cc_addresses=cc_emails, body=body,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)

                        participant.email_status = APP.EMAIL_SENT
                        participant.is_mail_sent = True
                        db.session.add(participant)
                        db.session.commit()
                        result = True
            # send emails to hosts
            hosts = WebcastHost.query.filter_by(
                webcast_id=row_id, email_status=APP.EMAIL_NOT_SENT ).all()
            if hosts:
                for host in hosts:
                    if host.host_id:
                        host_user = User.query.filter_by(
                            row_id=host.host_id).first()
                        # if host is the creator do not
                        # send email again to creator
                        if host.host_id == webcast.creator.row_id:
                            continue
                        host_email = host_user.email
                        host_name = host_user.profile.first_name
                        time_zone = host_user.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    else:
                        host_email = host.host_email
                        host_name = host.host_first_name
                        time_zone = webcast.creator.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [host_email]
                    is_unsub = is_unsubscription(host_email,
                        APP.EVNT_WEBCAST, host)
                    if not is_unsub:
                        # content for hosts
                        subject, body, attachment, html, host_name =\
                            content_getter.get_host_content(
                                host_name, webcast, time_zone, host_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBCAST,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, cc_addresses=cc_emails, body=body,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)

                        host.email_status = APP.EMAIL_SENT
                        host.is_mail_sent = True
                        db.session.add(host)
                        db.session.commit()
                        result = True
            # send emails to rsvps
            rsvps = WebcastRSVP.query.filter_by(
                webcast_id=row_id, email_status=APP.EMAIL_NOT_SENT).all()
            if rsvps:
                for rsvp in rsvps:
                    rsvp_email = rsvp.email
                    to_addresses = [rsvp_email]
                    # if rsvp is the creator do not send email again to creator
                    if rsvp_email == webcast.creator.email:
                        continue
                    rsvp_name = rsvp.contact_person
                    is_unsub = is_unsubscription(rsvp_email,
                        APP.EVNT_WEBCAST, rsvp)
                    if not is_unsub:
                        # content for rsvps
                        subject, body, attachment, html, rsvp_name =\
                            content_getter.get_rsvp_content(rsvp_name, webcast,
                                rsvp_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBCAST,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, cc_addresses=cc_emails, body=body,
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
            webcast.is_in_process = False
            db.session.add(webcast)
            db.session.commit()

    return result


@celery_app.task(bind=True, ignore_result=True)
def send_webcast_event_new_invitee_email(
        self, result, row_id, invitee_list, invitee_ids, *args, **kwargs):
    """
    Sends the webcast new invitee email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the corporate_access_event for which email is to be
        generated
    """

    if result:
        try:
            webcast = Webcast.query.get(row_id)
            if webcast is None:
                logger.exception('Webcast does not exist')
                return False

            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            smtp_settings = get_smtp_settings(webcast.created_by)
            # initialize
            content_getter = LaunchContent(webcast)
            event_url = generate_event_book_email_link(
                current_app.config['WEBCAST_EVENT_JOIN_ADD_URL'], webcast)
            ics_param = {
                "summery": webcast.title,
                "dtstart": webcast.started_at,
                "dtend": webcast.ended_at,
                "description": webcast.description + '\n' + event_url}
            ics_file = generate_ics_file(**ics_param)
            # cc email list
            cc_emails = []
            if webcast.cc_emails:
                cc_emails = list(set(webcast.cc_emails))

            # send emails to invitees
            invitees = WebcastInvitee.query.filter_by(
                webcast_id=row_id).all()
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
                        time_zone = webcast.creator.settings.timezone or \
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [invitee_email]
                    is_unsub = is_unsubscription(invitee_email,
                        APP.EVNT_WEBCAST, invitee)
                    if not is_unsub:
                        subject, body, attachment, html, invitee_name = content_getter. \
                            get_invitee_content(invitee_name, webcast,
                                                time_zone, invitee,
                                                invitee_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBCAST,
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
            webcast.is_in_process = False
            db.session.add(webcast)
            db.session.commit()

        return result


@celery_app.task(bind=True, ignore_result=True)
def send_webcast_completion_email(self, result, row_id, *args, **kwargs):
    """
    Sends the webcast completion related email.

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the webcast row id
    """
    if result:
        try:
            webcast = Webcast.query.get(row_id)
            if webcast is None:
                logger.exception('webcast does not exist')
                return False
            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            smtp_settings = get_smtp_settings(webcast.created_by)
            # initialize
            content_getter = CompletionContent()
            # cc email list
            cc_emails = []
            if webcast.cc_emails:
                cc_emails = list(set(webcast.cc_emails))
            # send emails to participants
            participants = WebcastParticipant.query.filter_by(
                webcast_id=row_id).all()
            if participants:
                for participant in participants:
                    if participant.participant_id:
                        participant_user = User.query.filter_by(
                            row_id=participant.participant_id).first()
                        # if participant is the creator do not
                        # send email again to creator
                        if participant.participant_id == \
                                webcast.creator.row_id:
                            continue
                        participant_email = participant_user.email
                        participant_name = participant_user.profile.first_name
                    else:
                        participant_email = participant.participant_email
                        participant_name = participant.participant_first_name
                    to_addresses = [participant_email]
                    is_unsub = is_unsubscription(participant_email,
                        APP.EVNT_WEBCAST)
                    if not is_unsub:
                        subject, body, attachment, html, participant_name = \
                            content_getter.get_participant_content(
                                participant_name, webcast, participant_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBCAST,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, cc_addresses=cc_emails, body=body,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings)
                        result = True
            # send emails to attendee
            attendees = WebcastAttendee.query.filter_by(
                webcast_id=row_id).all()
            if attendees:
                for attendee in attendees:
                    if attendee.attendee_id:
                        attendee_email = attendee.attendee.email
                        attendee_name = attendee.attendee.profile.first_name
                    to_addresses = [attendee_email]
                    is_unsub = is_unsubscription(attendee_email,
                        APP.EVNT_WEBCAST)
                    if not is_unsub:
                        subject, body, attachment, html, attendee_name =\
                            content_getter.get_attendee_content(
                                attendee_name, webcast, attendee_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBCAST,
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
def send_webcast_update_email(self, result, row_id, new_emails,
                              new_invitee_ids, *args, **kwargs):
    """
    Sends the webcast update related email.

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the webcast row id
    """
    if result:
        try:
            webcast = Webcast.query.get(row_id)
            if webcast is None:
                logger.exception('Webcast does not exist')
                return False
            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            smtp_settings = get_smtp_settings(webcast.created_by)
            # initialize
            content_getter = UpdateContent(webcast)
            # cc email list
            cc_emails = []
            if webcast.cc_emails:
                cc_emails = list(set(webcast.cc_emails))
            # first send to creator
            creator_name = webcast.creator.profile.first_name
            time_zone = webcast.creator.settings.timezone or\
                current_app.config['USER_DEFAULT_TIMEZONE']
            to_addresses = [webcast.creator.email]
            event_url = generate_event_book_email_link(
                current_app.config['WEBCAST_EVENT_JOIN_ADD_URL'],
                webcast)
            ics_param = {
                "summery": webcast.title,
                "dtstart": webcast.started_at,
                "dtend": webcast.ended_at,
                "description": webcast.description + '\n' + event_url}
            ics_file = generate_ics_file(**ics_param)
            is_unsub = is_unsubscription(to_addresses[0],
                APP.EVNT_WEBCAST)
            if not is_unsub:
                # content for creator
                subject, body, attachment, html, creator_name = content_getter.\
                    get_content(creator_name, webcast, time_zone,
                                to_addresses[0])
                send_email_actual(
                    subject=subject, keywords=APP.WEBCAST,
                    from_name=from_name, from_email=from_email,
                    to_addresses=to_addresses, reply_to=reply_to,
                    cc_addresses=cc_emails, body=body,
                    html=html, attachment=attachment,
                    smtp_settings=smtp_settings, ics_file=ics_file)
                result = True
            # send emails to invitees
            invitees = WebcastInvitee.query.filter_by(webcast_id=row_id).all()
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
                        time_zone = webcast.creator.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [invitee_email]
                    is_unsub = is_unsubscription(invitee_email,
                        APP.EVNT_WEBCAST)
                    if not is_unsub:
                        subject, body, attachment, html, invitee_name = content_getter.\
                            get_invitee_content(
                                invitee_name, webcast, time_zone, event_url,
                                invitee_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBCAST,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body, cc_addresses=cc_emails,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)
                        result = True
            # send emails to participants
            participants = WebcastParticipant.query.filter_by(
                webcast_id=row_id).all()
            if participants:
                for participant in participants:
                    if participant.participant_id:
                        participant_user = User.query.filter_by(
                            row_id=participant.participant_id).first()
                        # if participant is the creator do not
                        # send email again to creator
                        if participant.participant_id == \
                                webcast.creator.row_id:
                            continue
                        participant_email = participant_user.email
                        participant_name = participant_user.profile.first_name
                        time_zone = participant_user.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    else:
                        participant_email = participant.participant_email
                        participant_name = participant.participant_first_name
                        time_zone = webcast.creator.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [participant_email]
                    is_unsub = is_unsubscription(participant_email,
                        APP.EVNT_WEBCAST)
                    if not is_unsub:
                        subject, body, attachment, html, participant_name = \
                            content_getter.get_content(
                                participant_name, webcast, time_zone,
                                participant_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBCAST,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body, cc_addresses=cc_emails,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)
                        result = True
            # send emails to hosts
            hosts = WebcastHost.query.filter_by(webcast_id=row_id).all()
            if hosts:
                for host in hosts:
                    if host.host_id:
                        host_user = User.query.filter_by(
                            row_id=host.host_id).first()
                        # if host is the creator do not
                        # send email again to creator
                        if host.host_id == webcast.creator.row_id:
                            continue
                        host_email = host_user.email
                        host_name = host_user.profile.first_name
                        time_zone = host_user.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    else:
                        host_email = host.host_email
                        host_name = host.host_first_name
                        time_zone = webcast.creator.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [host_email]
                    is_unsub = is_unsubscription(host_email,
                        APP.EVNT_WEBCAST)
                    if not is_unsub:
                        # content for hosts
                        subject, body, attachment, html, host_name =\
                            content_getter.get_content(
                                host_name, webcast, time_zone, host_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBCAST,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body, cc_addresses=cc_emails,
                            html=html, attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)
                        result = True
            # send emails to rsvps
            rsvps = WebcastRSVP.query.filter_by(webcast_id=row_id).all()
            if rsvps:
                for rsvp in rsvps:
                    rsvp_email = rsvp.email
                    # if rsvp is the creator do not send email again to creator
                    if rsvp_email == webcast.creator.email:
                        continue
                    to_addresses = [rsvp_email]
                    rsvp_name = rsvp.contact_person
                    timezone = None
                    is_unsub = is_unsubscription(rsvp_email,
                        APP.EVNT_WEBCAST)
                    if not is_unsub:
                        # content for rsvps
                        subject, body, attachment, html, rsvp_name =\
                            content_getter.get_content(rsvp_name, webcast,
                                timezone, rsvp_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBCAST,
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
def send_webcast_cancelled_email(self, result, row_id, *args, **kwargs):
    """
    Sends the webcast cancelled related email.

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the webcast row id
    """
    if result:
        try:
            webcast = Webcast.query.get(row_id)
            if webcast is None:
                logger.exception('Webcast does not exist')
                return False
            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            smtp_settings = get_smtp_settings(webcast.created_by)
            # initialize
            content_getter = CancellationContent(webcast)
            # cc email list
            cc_emails = []
            if webcast.cc_emails:
                cc_emails = list(set(webcast.cc_emails))
            event_url = generate_event_book_email_link(
                current_app.config['WEBCAST_EVENT_JOIN_ADD_URL'],
                webcast)
            # send emails to invitees
            invitees = WebcastInvitee.query.filter_by(webcast_id=row_id).all()
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
                        time_zone = webcast.creator.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [invitee_email]
                    is_unsub = is_unsubscription(invitee_email,
                        APP.EVNT_WEBCAST)
                    if not is_unsub:
                        subject, body, attachment, html, invitee_name = content_getter.\
                            get_invitee_content(
                                invitee_name, webcast, time_zone, event_url,
                                invitee_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.WEBCAST,
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
