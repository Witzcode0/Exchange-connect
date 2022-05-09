"""
Schemas for "webinar rsvps" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, webinar_fields)
from app.base import constants as APP
from app.webinar_resources.webinar_rsvps import constants as WEBINARRSVP
from app.webinar_resources.webinar_rsvps.models import WebinarRSVP


class WebinarRSVPSchema(ma.ModelSchema):
    """
    Schema for loading "webinar rsvp" from request,
    and also formatting output
    """
    email = field_for(
        WebinarRSVP, 'email', field_class=fields.Email,
        validate=[validate.Length(max=WEBINARRSVP.EMAIL_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])
    contact_person = field_for(
        WebinarRSVP, 'contact_person',
        validate=[validate.Length(max=WEBINARRSVP.CONTACT_PERSON_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])
    phone = field_for(
        WebinarRSVP, 'phone',
        validate=[validate.Length(max=WEBINARRSVP.PHONE_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])
    sequence_id = field_for(
        WebinarRSVP, 'sequence_id', validate=validate.Range(
            min=APP.SEQUENCE_ID_MIN_VALUE,
            error=APP.SEQUENCE_ID_MIN_VALUE_ERROR))

    class Meta:
        model = WebinarRSVP
        include_fk = True
        load_only = ('updated_by', 'created_by',)
        dump_only = default_exclude + ('updated_by', 'created_by',
                    'conference_url', 'is_mail_sent','email_status')

    links = ma.Hyperlinks({
        'self': ma.URLFor(
            'webinar_api.webinarrsvpapi', row_id='<row_id>'),
        'collection': ma.URLFor('webinar_api.webinarrsvplistapi')
    }, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)

    webinar = ma.Nested(
        'app.webinar_resources.webinars.schemas.WebinarSchema',
        only=webinar_fields, dump_only=True)


class WebinarRSVPReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "webinar rsvp" filters from request args
    """
    webinar_id = fields.Integer(load_only=True)
