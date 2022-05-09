"""
surveys related email tasks
"""

from flask import current_app
from app import db

from app.common.helpers import generate_event_book_email_link
from app.survey_resources.surveys.models import Survey
from app.survey_resources.survey_responses.models import SurveyResponse
from app.resources.users.models import User
from app.resources.email_credentials.helpers import get_smtp_settings

from queueapp.tasks import celery_app, logger, send_email_actual
from queueapp.surveys.email_contents import (
    LaunchContent, CompletionContent)
from app.base import constants as APP
from app.resources.unsubscriptions.helpers import is_unsubscription


@celery_app.task(bind=True, ignore_result=True)
def send_survey_launch_email(self, result, row_id, *args, **kwargs):
    """
    Sends the survey related email.

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the survey row id
    """
    if result:
        try:
            survey = Survey.query.get(row_id)
            if survey is None:
                logger.exception('survey does not exist')
                return False
            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''

            # initialize
            content_getter = LaunchContent()
            # cc email list
            cc_emails = []
            if survey.cc_emails:
                cc_emails = list(set(survey.cc_emails))

            smtp_settings = get_smtp_settings(survey.created_by)
            # #TODO: to be decided whether to remove it or keep it
            """
            # first send email to creator
            creator_name = survey.creator.profile.first_name
            to_addresses = [survey.creator.email] + cc_emails
            is_unsub = is_unsubscription(to_addresses[0],APP.EVNT_SURVEY)
            if not is_unsub:
                # content for creator
                subject, body, attachment, html, creator_name = content_getter.\
                    get_creator_content(creator_name, survey)
                send_email_actual(
                    subject=subject,
                    from_name=from_name, from_email=from_email,
                    to_addresses=to_addresses, reply_to=reply_to, body=body,
                    html=html, attachment=attachment, 
                    smtp_settings=smtp_settings)
                result = True
            """

            # send emails to invitees
            s_invitees = SurveyResponse.query.filter_by(
                survey_id=row_id, email_status= APP.EMAIL_NOT_SENT).all()
            if s_invitees:
                for invitee in s_invitees:
                    if invitee.user_id:
                        invited_user = User.query.filter_by(
                            row_id=invitee.user_id).first()
                        invitee_email = invited_user.email
                        invitee_name = invited_user.profile.first_name
                    else:
                        invitee_email = invitee.email
                        invitee_name = invitee.first_name
                    to_addresses = [invitee_email] + cc_emails
                    is_unsub = is_unsubscription(invitee_email,
                        APP.EVNT_SURVEY, invitee)
                    if not is_unsub:
                        subject, body, attachment, html, invitee_name = content_getter.\
                            get_invitee_content(invitee_name, survey, invitee,
                                invitee_email)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.SURVEY_EMAIL,
                            from_email=from_email, to_addresses=to_addresses,
                            reply_to=reply_to, body=body, html=html,
                            attachment=attachment, smtp_settings=smtp_settings)

                        invitee.email_status = APP.EMAIL_SENT
                        invitee.is_mail_sent = True
                        db.session.add(invitee)
                        db.session.commit()
                        result = True

        except Exception as e:
            raise e
            logger.exception(e)
            result = False

        finally:
            survey.is_in_process = False
            db.session.add(survey)
            db.session.commit()

    return result


@celery_app.task(bind=True, ignore_result=True)
def send_survey_completion_email(self, result, row_id, *args, **kwargs):
    """
    Sends the survey completion related email.

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the survey response row id
    """
    if result:
        try:
            survey_resp = SurveyResponse.query.get(row_id)
            if survey_resp is None:
                logger.exception('survey response does not exist')
                return False
            # generate the email content
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            reply_to = ''
            # initialize
            content_getter = CompletionContent(self)
            smtp_settings = get_smtp_settings(survey_resp.survey.created_by)
            # send emails to survey responded
            if survey_resp.user_id:
                responed_user = User.query.filter_by(
                    row_id=survey_resp.user_id).first()
                responder_email = responed_user.email
                responder_name = responed_user.profile.first_name
            else:
                responder_email = survey_resp.email
                responder_name = survey_resp.first_name + survey_resp.last_name
            to_addresses = [responder_email]
            is_unsub = is_unsubscription(responder_email, APP.EVNT_SURVEY)
            if not is_unsub:
                subject, body, attachment, html, responder_name = content_getter.\
                    get_responded_content(responder_name)
                send_email_actual(
                    subject=subject, from_name=from_name,
                    keywords=APP.SURVEY_EMAIL,
                    from_email=from_email, to_addresses=to_addresses,
                    reply_to=reply_to, body=body, html=html,
                    attachment=attachment, smtp_settings=smtp_settings)
                result = True

        except Exception as e:
            raise e
            logger.exception(e)
            result = False

    return result
