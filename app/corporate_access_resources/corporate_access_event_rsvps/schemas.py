"""
Schemas for "corporate_access_event rsvps" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, ca_event_fields)
from app.base import constants as APP
from app.corporate_access_resources.corporate_access_event_rsvps \
    import constants as CORPACCESS_RSVP
from app.corporate_access_resources.corporate_access_event_rsvps.models \
    import CorporateAccessEventRSVP


class CorporateAccessEventRSVPSchema(ma.ModelSchema):
    """
    Schema for loading "corporate access event rsvp" from request,
    and also formatting output
    """
    email = field_for(
        CorporateAccessEventRSVP, 'email', field_class=fields.Email,
        validate=[validate.Length(max=CORPACCESS_RSVP.EMAIL_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])
    contact_person = field_for(
        CorporateAccessEventRSVP, 'contact_person',
        validate=[validate.Length(
            max=CORPACCESS_RSVP.CONTACT_PERSON_MAX_LENGTH,
            error=APP.MSG_LENGTH_EXCEEDS)])
    phone = field_for(
        CorporateAccessEventRSVP, 'phone',
        validate=[validate.Length(max=CORPACCESS_RSVP.PHONE_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])
    sequence_id = field_for(
        CorporateAccessEventRSVP, 'sequence_id',
        validate=validate.Range(
            min=APP.SEQUENCE_ID_MIN_VALUE,
            error=APP.SEQUENCE_ID_MIN_VALUE_ERROR))

    class Meta:
        model = CorporateAccessEventRSVP
        include_fk = True
        load_only = ('created_by', 'updated_by')
        dump_only = default_exclude + ('created_by', 'updated_by',
            'is_mail_sent', 'email_status')

    links = ma.Hyperlinks({
        'self': ma.URLFor(
            'corporate_access_api.corporateaccesseventrsvpapi',
            row_id='<row_id>'),
        'collection': ma.URLFor(
            'corporate_access_api.corporateaccesseventrsvplistapi')
    }, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    corporate_access_event = ma.Nested(
        'app.corporate_access_resources.'
        'corporate_access_events.schemas.CorporateAccessEventSchema',
        only=ca_event_fields, dump_only=True)


class CorporateAccessEventRSVPReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "corporate access event rsvp" filters from request args
    """
    corporate_access_event_id = fields.Integer(load_only=True)
