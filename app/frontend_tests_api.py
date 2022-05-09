"""
API endpoints for "frontend tests" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app
from flask_restful import abort
from marshmallow import fields, validate, pre_load, ValidationError

from app import ma, c_abort
from app.base.api import BaseResource
from app.common.utils import send_email
from app.base import constants as APP


class FETestSchema(ma.Schema):
    """
    Schema for sending email for tests
    """
    email = fields.Email(required=True)
    subject = fields.String(required=True)
    html = fields.String()
    text = fields.String()
    from_type = fields.String(required=True,
                              validate=validate.OneOf(APP.TEST_MAIL_TYPES))

    @pre_load(pass_many=False)
    def subject_or_mail(self, data):
        if not 'html' in data and not 'text' in data:
            raise ValidationError('Provide text or html')


class FrontendEmailTestsAPI(BaseResource):
    """
    Put API for sending frontend email tests, only for testing.
    """

    def put(self):
        """
        Send an email
        """
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input
            data, errors = FETestSchema().load(json_data)
            if errors:
                c_abort(422, errors=errors)

            subject = data['subject']
            text = data['text'] if 'text' in data else ''
            html = data['html'] if 'html' in data else ''
            to_addresses = [data['email']]
            from_name = current_app.config['DEFAULT_CA_SENDER_NAME']
            from_email = current_app.config['DEFAULT_CA_SENDER_EMAIL']
            if data['from_type'] == APP.DF_SUPPORT:
                from_name = current_app.config['DEFAULT_SENDER_NAME']
                from_email = current_app.config['DEFAULT_SENDER_EMAIL']

            reply_to = ''
            attachment = ''
            # send user email
            if not current_app.config['DEBUG']:
                send_email(current_app.config['SMTP_USERNAME'],
                           current_app.config['SMTP_PASSWORD'],
                           current_app.config['SMTP_HOST'],
                           subject=subject, from_name=from_name,
                           from_email=from_email, to_addresses=to_addresses,
                           reply_to=reply_to, body=text, html=html,
                           attachment=attachment)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'mail sent'}, 200
