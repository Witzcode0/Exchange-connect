"""
Distribution List related tasks, for each type of email
"""

import os
import requests
import datetime

from flask import current_app
from sqlalchemy import and_

from app import db
from app.common.utils import delete_fs_file
from app.crm_resources.crm_distribution_lists.models import CRMDistributionList
from app.crm_resources.crm_distribution_invitee_lists.models import (
    CRMDistributionInviteeList)
from app.base import constants as APP
from app.resources.email_credentials.helpers import get_smtp_settings

from queueapp.tasks import celery_app, logger, send_email_actual
from app.resources.unsubscriptions.helpers import (
    generate_unsubscribe_email_link)
from app.resources.unsubscriptions.helpers import is_unsubscription


@celery_app.task(bind=True, ignore_result=True, soft_time_limit=10000)
def send_distribution_invitee_list_email(
        self, result, row_id, *args, **kwargs):
    """
    Sends the Distribution List invitees related email
    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the distribution list for which email is to be
        generated
    """

    if result:
        try:
            distribution_list_data = CRMDistributionList.query.get(row_id)
            if not distribution_list_data:
                logger.exception('Distribution list does not exist')
                return False
            # get attachment files
            files = []
            if distribution_list_data.attachments:
                distribution_list_data.load_urls()
                for name, attach_url in zip(
                        distribution_list_data.attachments,
                        distribution_list_data.attachment_urls):
                    response = requests.get(attach_url)
                    file = os.path.join(
                        current_app.config['BASE_DOWNLOADS_FOLDER'], name)
                    with open(file, 'wb') as f:
                        f.write(response.content)
                        files.append(file)
            with open('email_html_docs/dist_list_template'
                      '.html', 'r') as htmlfile:
                htmlfile = htmlfile.read()
            # generate the email content
            # default sender details
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            # get the sender details, incase it is set in account_settings
            acc_setts = distribution_list_data.account.settings  # account settings
            if (acc_setts.event_sender_email and
                    acc_setts.event_sender_name and acc_setts.verified_status):
                # #TODO: always reverify, before sending
                from_name = acc_setts.event_sender_name
                from_email = acc_setts.event_sender_email

            reply_to = ''
            subject = current_app.config['BRAND_NAME'] + '-' + \
                distribution_list_data.campaign_name
            attachment = files
            body = ''
            # fetch all invitee details
            distribution_invitee = CRMDistributionInviteeList.query.filter(
                and_(
                    CRMDistributionInviteeList.distribution_list_id == row_id,
                    CRMDistributionInviteeList.email_status == \
                    APP.EMAIL_NOT_SENT)).all()
            if distribution_invitee:
                html_teplate = distribution_list_data.html_template
                dynamic_body = {'body': html_teplate}
                for invitee in distribution_invitee:
                    is_unsub = is_unsubscription(invitee.invitee_email,
                        APP.EVNT_DIST_LIST, invitee)
                    if not is_unsub:
                        unsub_url = generate_unsubscribe_email_link(
                            invitee.invitee_email)
                        dynamic_body['unsubscribe'] = unsub_url
                        html = htmlfile.format(**dynamic_body)
                        smtp_settings = get_smtp_settings(
                            distribution_list_data.created_by)
                        send_email_actual(
                            subject=subject, from_name=from_name,
                            keywords=APP.DISTRIBUTION_EMAIL_TASK,
                            from_email=from_email,
                            to_addresses=[invitee.invitee_email],
                            reply_to=reply_to, body=body, html=html,
                            attachment=attachment, smtp_settings=smtp_settings)
                        # for mail sent or not to invitee
                        invitee.email_status = APP.EMAIL_SENT
                        invitee.sent_on = datetime.datetime.utcnow()
                        invitee.is_mail_sent = True
                        db.session.add(invitee)
                        db.session.commit()
            if attachment:
                for attach in attachment:
                    delete_fs_file(attach)
            result = True
        except Exception as e:
            raise e
            logger.exception(e)
            result = False

        return result
