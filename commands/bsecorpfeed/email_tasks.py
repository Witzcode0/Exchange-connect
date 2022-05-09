"""
BSE - send an email when new descriptor added while fetching new bse announcements
"""

from flask import current_app, render_template
from queueapp.tasks import celery_app, logger, send_email_actual
from app.base import constants as APP

def send_bse_new_descriptor_added_email(
        self, result, list, *args, **kwargs):
    """
    Sends the descriptor added email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param list:
        list of descriptors which are newly added.
    """
    if result:
        try:
            # generate the email content
            from_name = current_app.config['DEFAULT_SENDER_NAME']
            from_email = current_app.config['DEFAULT_SENDER_EMAIL']
            to_addresses = current_app.config['DESCRIPTOR_TO_ADDRESS']
            cc_emails = current_app.config['DESCRIPTOR_CC_ADDRESS']
            subject = "ExchangeConnect Admin - New descriptor has been added from BSE feed"

            descriptors = list

            html = render_template(
                'new_descriptor_email_template.html',
                descriptors=descriptors)

            send_email_actual(
                subject=subject, from_name=from_name,
                keywords=APP.NEW_DESCRIPTOR,
                from_email=from_email, to_addresses=to_addresses,
                cc_addresses=cc_emails,
                html=html)

        except Exception as e:
            raise e
            logger.exception(e)
            result = False
        return result
