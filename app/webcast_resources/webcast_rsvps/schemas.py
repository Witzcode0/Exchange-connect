"""
Schemas for "webcast rsvps" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, webcast_fields)
from app.base import constants as APP
from app.webcast_resources.webcast_rsvps import constants as WEBCASTRSVP
from app.webcast_resources.webcast_rsvps.models import WebcastRSVP


class WebcastRSVPSchema(ma.ModelSchema):
    """
    Schema for loading "webcast rsvp" from request,
    and also formatting output
    """
    email = field_for(
        WebcastRSVP, 'email', field_class=fields.Email,
        validate=[validate.Length(max=WEBCASTRSVP.EMAIL_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])
    contact_person = field_for(
        WebcastRSVP, 'contact_person',
        validate=[validate.Length(max=WEBCASTRSVP.CONTACT_PERSON_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])
    phone = field_for(
        WebcastRSVP, 'phone',
        validate=[validate.Length(max=WEBCASTRSVP.PHONE_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])
    sequence_id = field_for(
        WebcastRSVP, 'sequence_id', validate=validate.Range(
            min=APP.SEQUENCE_ID_MIN_VALUE,
            error=APP.SEQUENCE_ID_MIN_VALUE_ERROR))

    class Meta:
        model = WebcastRSVP
        include_fk = True
        load_only = ('updated_by', 'created_by',)
        dump_only = default_exclude + ('updated_by', 'created_by',
                    'is_mail_sent','email_status')

    links = ma.Hyperlinks({
        'self': ma.URLFor(
            'webcast_api.webcastrsvpapi', row_id='<row_id>'),
        'collection': ma.URLFor('webcast_api.webcastrsvplistapi')
    }, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)

    webcast = ma.Nested(
        'app.webcast_resources.webcasts.schemas.WebcastSchema', dump_only=True,
        only=webcast_fields)


class WebcastRSVPReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "webcast rsvp" filters from request args
    """
    webcast_id = fields.Integer(load_only=True)
