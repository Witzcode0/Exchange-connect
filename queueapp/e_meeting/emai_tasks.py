"""
emeeting related email tasks, for each type of email
"""
import os
import shutil

from flask import current_app

from app.base import constants as APP
from app.toolkit_resources.project_e_meeting.models import Emeeting
from app.toolkit_resources.project_e_meeting_invitee.models import EmeetingInvitee
from app.resources.users.models import User
from app.common.helpers import generate_event_book_email_link
from app import db
from app.resources.email_credentials.helpers import get_smtp_settings
from app.common.helpers import generate_ics_file

from queueapp.tasks import celery_app, logger, send_email_actual
from queueapp.e_meeting.email_contents import (
    LaunchEmeetingContent, CancellationContent, UpdateContent)
from app.resources.unsubscriptions.helpers import is_unsubscription


@celery_app.task(bind=True, ignore_result=True)
def send_emeeting_launch_email(self, result, row_id, *args, **kwargs):
    """
    Sends the emeeting related email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the emeeting for which email is to be generated
    """
    if result:
        try:
            emeeting = Emeeting.query.get(row_id)
            if emeeting is None:
                logger.exception('Emeeting does not exist')
                return False
            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            smtp_settings = get_smtp_settings(emeeting.created_by)
            # initialize
            content_getter = LaunchEmeetingContent(emeeting)
            time_zone = emeeting.creator.settings.timezone or\
                current_app.config['USER_DEFAULT_TIMEZONE']
        
            event_url = generate_event_book_email_link(
                current_app.config['EMEETING_EVENT_JOIN_ADD_URL'],
                emeeting)
            ics_param = {
                "summery": emeeting.meeting_subject,
                "dtstart": emeeting.meeting_datetime,
                "description": emeeting.meeting_agenda + '\n' + event_url}
            ics_file = generate_ics_file(**ics_param)
            
            # if not emeeting.creator_mail_sent :
                # first send to creator
            creator_name = emeeting.creator.profile.first_name
            time_zone = emeeting.creator.settings.timezone
            to_addresses = [emeeting.creator.email]
            is_unsub = is_unsubscription(to_addresses[0], APP.EVNT_EMEETING)
            if not is_unsub and not emeeting.creator_mail_sent:
                # content for creator
                subject, body, attachment, html, creator_name = content_getter.\
                    get_creator_content(
                        creator_name, emeeting, time_zone, to_addresses[0],
                        event_url)
                send_email_actual(
                    subject=subject, keywords=APP.EMEETING_EMAIL_TASK,
                    from_name=from_name, from_email=from_email,
                    to_addresses=to_addresses, reply_to=reply_to, body=body,
                    html=html,attachment=attachment, smtp_settings=smtp_settings,
                    ics_file=ics_file)
                emeeting.creator_mail_sent = True
                db.session.add(emeeting)
                db.session.commit()
                result = True
            # send emails to invitees
            invitees = EmeetingInvitee.query.filter_by(
                e_meeting_id=row_id, email_status=APP.EMAIL_NOT_SENT).all()
            if invitees:
                for invitee in invitees:
                    if not invitee.is_mail_sent: 
                        if invitee.invitee_id:
                            invited_user = User.query.filter_by(
                                row_id=invitee.invitee_id).first()
                            invitee_email = invited_user.email
                            invitee_name = invited_user.profile.first_name
                            time_zone = invited_user.settings.timezone or\
                                current_app.config['USER_DEFAULT_TIMEZONE']
                        to_addresses = [invitee_email]
                        is_unsub = is_unsubscription(invitee_email,
                            APP.EVNT_EMEETING, invitee)
                        if not is_unsub:
                            subject, body, attachment, html, invitee_name = content_getter.\
                                get_invitee_content(
                                    invitee_name, emeeting, time_zone, event_url,
                                    invitee_email)
                            send_email_actual(
                                subject=subject, from_name=from_name,
                                keywords=APP.EMEETING_EMAIL_TASK,
                                from_email=from_email, to_addresses=to_addresses,
                                reply_to=reply_to, body=body,
                                html=html, attachment=attachment,
                                smtp_settings=smtp_settings, ics_file=ics_file)

                            invitee.email_status = APP.EMAIL_SENT
                            invitee.is_mail_sent = True
                            db.session.add(invitee)
                            db.session.commit()
                            result = True
            
            shutil.rmtree(os.path.dirname(ics_file))
        except Exception as e:
            raise e
            logger.exception(e)
            result = False

        finally:
            emeeting.is_in_process = False
            db.session.add(emeeting)
            db.session.commit()

    return result


@celery_app.task(bind=True, ignore_result=True)
def send_emeeting_cancellation_email(self, result, row_id, *args, **kwargs):
    """
    Sends the emeeting cancellation email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the emeeting for which email is to be generated
    """
    if result:
        try:
            emeeting = Emeeting.query.get(row_id)
            if emeeting is None:
                logger.exception('Emeeting does not exist')
                return False
            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            smtp_settings = get_smtp_settings(emeeting.created_by)
            # initialize
            content_getter = CancellationContent(emeeting)
            event_url = generate_event_book_email_link(
                current_app.config['EMEETING_EVENT_JOIN_ADD_URL'],
                emeeting)
            
            # send emails to invitees
            invitees = EmeetingInvitee.query.filter_by(e_meeting_id=row_id).all()
            if invitees:
                for invitee in invitees:
                    if invitee.invitee_id:
                        invited_user = User.query.filter_by(
                            row_id=invitee.invitee_id).first()
                        invitee_email = invited_user.email
                        invitee_name = invited_user.profile.first_name
                        time_zone = invited_user.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [invitee_email]
                    is_unsub = is_unsubscription(invitee_email,
                        APP.EVNT_EMEETING)
                    if not is_unsub:
                        subject, body, attachment, html, invitee_name = content_getter.\
                            get_invitee_content(
                                invitee_name, emeeting, time_zone, event_url,
                                invitee_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.EMEETING_EMAIL_TASK,
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
def send_emeeting_update_email(self, result, row_id, rescheduled, *args, **kwargs):
    """
    Sends the emeeting update email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the emeeting for which email is to be generated
    """
    if result:
        try:
            emeeting = Emeeting.query.get(row_id)
            if emeeting is None:
                logger.exception('Emeeting does not exist')
                return False
            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            smtp_settings = get_smtp_settings(emeeting.created_by)
            # initialize
            content_getter = UpdateContent(emeeting, rescheduled)
            event_url = generate_event_book_email_link(
                current_app.config['EMEETING_EVENT_JOIN_ADD_URL'],
                emeeting)
            ics_param = {
                "summery": emeeting.meeting_subject,
                "dtstart": emeeting.meeting_datetime,
                "description": emeeting.meeting_agenda + '\n' + event_url}
            ics_file = generate_ics_file(**ics_param)
            
            # first send to creator
            creator_name = emeeting.creator.profile.first_name
            to_addresses = [emeeting.creator.email]
            time_zone = emeeting.creator.settings.timezone or\
                current_app.config['USER_DEFAULT_TIMEZONE']
            is_unsub = is_unsubscription(to_addresses[0], APP.EVNT_EMEETING)
            if not is_unsub:
                # content for creator
                subject, body, attachment, html, creator_name = content_getter.\
                    get_creator_content(
                        creator_name, emeeting, time_zone, to_addresses[0],
                        event_url)
                send_email_actual(
                    subject=subject, keywords=APP.EMEETING_EMAIL_TASK,
                    from_name=from_name, from_email=from_email,
                    to_addresses=to_addresses, reply_to=reply_to, body=body,
                    html=html, attachment=attachment,
                    smtp_settings=smtp_settings, ics_file=ics_file)
                result = True
            # send emails to invitees
            invitees = EmeetingInvitee.query.filter_by(e_meeting_id=row_id).all()
            if invitees:
                for invitee in invitees:
                    if invitee.invitee_id:
                        invited_user = User.query.filter_by(
                            row_id=invitee.invitee_id).first()
                        invitee_email = invited_user.email
                        invitee_name = invited_user.profile.first_name
                        time_zone = invited_user.settings.timezone or\
                            current_app.config['USER_DEFAULT_TIMEZONE']
                    to_addresses = [invitee_email]
                    is_unsub = is_unsubscription(invitee_email,
                        APP.EVNT_EMEETING)
                    if not is_unsub:
                        subject, body, attachment, html, invitee_name = content_getter.\
                            get_invitee_content(
                                invitee_name, emeeting, time_zone, event_url,
                                invitee_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.EMEETING_EMAIL_TASK,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body,html=html,
                            attachment=attachment,
                            smtp_settings=smtp_settings, ics_file=ics_file)
                        result = True
            
            shutil.rmtree(os.path.dirname(ics_file))
        except Exception as e:
            raise e
            logger.exception(e)
            result = False

    return result