"""
Inquiry related tasks, for each type of email
"""

from flask import current_app
from datetime import datetime as dt

from app.common.utils import time_converter
from app.resources.inquiries.models import Inquiry

from queueapp.tasks import celery_app, logger, send_email_actual
from app.base import constants as APP


@celery_app.task(bind=True, ignore_result=True)
def send_inquiry_contact_us_email(self, result, row_id, *args, **kwargs):
    """
    Sends the inquiry contact us email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the inquiry
    """

    if result:
        try:
            # first find the inquiry
            model = Inquiry.query.get(row_id)
            if model is None:
                return False

            # generate the email content
            to_addresses = current_app.config['DEFAULT_INQUIRY_EMAILS']
            from_name = current_app.config['DEFAULT_SENDER_NAME']
            from_email = current_app.config['DEFAULT_SENDER_EMAIL']
            reply_to = ''
            subject = 'Inquiry Received from %(user_name)s'
            subject = subject % {'user_name': model.name}
            html = ''
            attachment = ''
            body = 'Hi Team, \r\n\r\n'
            body += 'We have received an inquiry. Please' + \
                    ' find the details below: \r\n\r\n'
            body += 'Date: %(date)s\r\n'
            body += 'Time: %(time)s\r\n\r\n'
            body += 'Name: %(user_name)s\r\n'
            body += 'Email: %(email)s\r\n'
            if model.contact_number:
                body += 'Contact Number: %(contact_number)s\r\n'
            if model.subject:
                body += 'Subject: %(subject)s\r\n'
            if model.message:
                body += 'Message: %(message)s\r\n'
            body += '\r\n'
            body += 'Regards,\r\n%(sign_off_name)s'
            date_time_obj = time_converter(model.created_date)
            date = dt.strftime(date_time_obj, '%d %B %Y')
            time = dt.strftime(date_time_obj, '%I:%M %p')
            body = body % {
                'date': date,
                'time': time,
                'user_name': model.name,
                'email': model.email,
                'subject': model.subject,
                'message': model.message,
                'contact_number': model.contact_number,
                'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME']}
            # send email to concerned people
            if not current_app.config['DEBUG']:
                send_email_actual(
                    subject=subject, from_name=from_name,
                    keywords=APP.INQUIRY_EMAIL,
                    from_email=from_email, to_addresses=to_addresses,
                    reply_to=reply_to, body=body, html=html,
                    attachment=attachment)

            result = True
        except Exception as e:
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def send_inquiry_plan_email(self, result, row_id, *args, **kwargs):
    """
    Sends the inquiry plan email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the inquiry
    """

    if result:
        try:
            # first find the inquiry
            model = Inquiry.query.get(row_id)
            if model is None:
                return False

            # generate the email content
            to_addresses = current_app.config['DEFAULT_INQUIRY_EMAILS']
            from_name = current_app.config['DEFAULT_SENDER_NAME']
            from_email = current_app.config['DEFAULT_SENDER_EMAIL']
            reply_to = ''
            subject = 'Exchange Connect %(plan)s inquiry ' + \
                'received from %(user_name)s'
            subject = subject % {
                'user_name': model.name, 'plan': model.major_sub_type}
            html = ''
            attachment = ''
            body = 'Hi, \r\n\r\n'
            body += 'We have received a plan inquiry from %(user_name)s.\r\n'
            body += 'Please find the details below: \r\n\r\n'
            body += 'Account Type: %(account_type)s\r\n'
            body += 'Contact Person: %(user_name)s\r\n'
            body += 'Contact Email: %(email)s\r\n'
            if model.creator.profile.phone_number:
                body += 'Contact Number: %(phone)s\r\n'
            body += 'Company Name: %(company)s\r\n'
            body += 'Plan Name: %(plan)s\r\n'
            body += '\r\n'
            body += 'Regards,\r\n%(sign_off_name)s'
            body = body % {
                'account_type': model.creator.account_type,
                'user_name': model.name, 'email': model.email,
                'phone': model.creator.profile.phone_number,
                'company': model.account.account_name,
                'plan': model.major_sub_type,
                'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME']}
            # send email to concerned people
            if not current_app.config['DEBUG']:
                send_email_actual(
                    subject=subject, from_name=from_name,
                    keywords=APP.INQUIRY_EMAIL,
                    from_email=from_email, to_addresses=to_addresses,
                    reply_to=reply_to, body=body, html=html,
                    attachment=attachment)

            result = True
        except Exception as e:
            logger.exception(e)
            result = False

    return result
