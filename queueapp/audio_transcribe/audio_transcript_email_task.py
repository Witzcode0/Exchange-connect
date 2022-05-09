"""
send email for audio transcript
"""
from flask import current_app, render_template
from datetime import datetime as dt
from datetime import date

from app import db
from app.common.utils import time_converter
from app.base import constants as APP
from app.resources.audio_transcribe.models import AudioTranscribe
from app.resources.audio_transcribe.helpers import generate_transcript_email_link


from queueapp.tasks import celery_app, logger, send_email_actual

@celery_app.task(bind=True, ignore_result=True)
def send_transcript_link_email(self, result, row_id, *args, **kwargs):
    """
        Sends the transcript link on the email

        :param result:
            the result of previous task when chaining. Remember to pass True, when
            called as first of chain, or individually.
        :param row_id:
            the row id of the audio transcript
        """
    if result:
        try:
            # first find the registration request
            model = AudioTranscribe.query.get(row_id)
            if model is None:
                return False
            to_addresses = [model.email]
            from_name = current_app.config['DEFAULT_SENDER_NAME']
            from_email = current_app.config['DEFAULT_SENDER_EMAIL']
            bcc_addresses = []
            reply_to = ''
            subject = 'Your Audio transcript is Ready!!'
            attachment = ''

            url = generate_transcript_email_link(model)
            # print(url)
            with open('email_html_docs/transcript_email_template.html', 'r') as htmlfile:
                htmlfile = htmlfile.read()

            html = htmlfile
            body ='Hello, \r\n' + \
                'your {filename} transcript !\r\n\r\n' + \
                'Download your transcript : {link} ' +\
                'Thank you'

            body_dict = {
                'filename': model.filename,
                'link': url
            }

            html_body = {
                'filename': model.filename,
                'link': url
            }

            body = body.format(**body_dict)
            html = html.format(**html_body)

            send_email_actual(
                subject=subject, from_name=from_name,
                keywords=APP.USER_ACTIVITY_EMAIL,
                from_email=from_email, to_addresses=to_addresses,
                bcc_addresses=bcc_addresses,
                reply_to=reply_to, body=body, html=html,
                attachment=attachment)

            model.email_status = True
            db.session.add(model)
            db.session.commit()

            return True

        except Exception as e:
            logger.exception(e)
            result = False

    return result