"""
Personalised video invitees email related tasks, for each type of email
"""

import time
import os
import shutil

from app.base import constants as APP
from flask import current_app
from sqlalchemy import and_

from app import db
from app.common.helpers import generate_event_book_email_link
from app.common.utils import delete_fs_file
from app.resources.email_credentials.helpers import get_smtp_settings

from app.corporate_access_resources.corporate_access_events.models import (
    CorporateAccessEvent)
from app.resources.personalised_video.models import (PersonalisedVideoMaster)
from app.resources.personalised_video_invitee.models import (PersonalisedVideoInvitee)

from queueapp.tasks import celery_app, logger, send_email_actual
from queueapp.personalised_video.email_contents import LaunchContent


@celery_app.task(bind=True, ignore_result=True)
def send_personalised_video_invitee_email(
        self, result, row_id, invitee_list, *args, **kwargs):
    """
       Sends the personalised video invitee related email

       :param result:
           the result of previous task when chaining. Remember to pass True, when
           called as first of chain, or individually.
       :param row_id:
           the row id of the corporate_access_event for which email is to be
           generated
       """

    if result:
        try:
            pr = PersonalisedVideoMaster.query.get(row_id)
            print(pr)
            if pr is None:
                logger.exception('personalised video does not exist')
                return False

                # generate the email content

            #current_app.config['DEFAULT_CA_SENDER_NAME']
            from_name = 'kajal'
            #current_app.config['DEFAULT_CA_SENDER_EMAIL']
            from_email = 'sunny.shah@arhamtechnosoft.co.in'
            reply_to = ''

            content_getter = LaunchContent(pr)
            subject = ''
            html = ''
            body = ''
            # invitees = PersonalisedVideoInvitee.query.filter_by(
            #     video_id=row_id,
            #     email_status=APP.EMAIL_NOT_SENT).all()
            #filter invitees using email status.. change emau
            invitees = PersonalisedVideoInvitee.query.filter_by(
                video_id=row_id).all()

            if invitees:
                for invitee in invitees:
                    if invitee.email not in invitee_list:
                        continue
                    invitee_email = invitee.email
                    invitee_name = invitee.first_name
                    to_addresses = [invitee_email]
                    # is_unsub = is_unsubscription(
                    #     invitee_email, APP.EVNT_CA_EVENT, invitee)

                    # if is_unsub:
                    #     continue

                    smtp_settings = get_smtp_settings(pr.created_by)
                    logger.info("smpt settings",smtp_settings)
                    subject, body, html, invitee_name = \
                        content_getter.get_invitee_content(
                            invitee_name, pr, invitee,
                            invitee_email)
                    sub = "this is test subject"
                    from_name = 's-ancial developer'
                    # to_addresses = 'kajal@s-ancil.com'
                    to_addresses = to_addresses

                    send_email_actual(
                        subject=sub, from_name=from_name,
                        from_email=from_email, to_addresses=to_addresses,
                        body=body, html=html,
                        smtp_settings=smtp_settings)
                    # for mail sent or not to user
                    #APP.EMAIL_SENT
                    invitee.email_status = True
                    print("invitee from tasks",invitee)
                    # invitee.is_mail_sent = True
                    db.session.add(invitee)
                    db.session.commit()
                result = True
        except Exception as e:
            logger.exception(e)
            raise e

            result = False

        # finally:
        #     invitee.is_in_process = False
        #     db.session.add(invitee)
        #     db.session.commit()
    return result
