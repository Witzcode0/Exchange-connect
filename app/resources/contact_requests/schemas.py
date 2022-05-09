"""
Schemas for "contact request" related models
"""

from flask import g
from marshmallow import fields, validate, validates_schema, ValidationError
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.resources.contact_requests.models import (
    ContactRequest, ContactRequestHistory)
from app.resources.contact_requests import constants as CONTACT
from app.resources.accounts import constants as ACCOUNT


class ContactRequestSchema(ma.ModelSchema):
    """
    Schema for loading "contact request" from request, and also formatting
    output
    """
    status = field_for(ContactRequest, 'status', validate=validate.OneOf(
        CONTACT.CREQ_STATUS_TYPES))

    class Meta:
        model = ContactRequest
        include_fk = True
        dump_only = default_exclude + ('sent_by', )
        exclude = ('contact_requested_j', )

    links = ma.Hyperlinks({
        'self': ma.URLFor('api.contactrequestapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.contactrequestlistapi')
    }, dump_only=True)

    sender = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    sendee = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    the_other = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)

    @validates_schema(pass_original=True)
    def validate_not_self_request(self, data, original_data):
        """
        Validate that request is not sent to self!
        """
        if data['sent_to'] == g.current_user['row_id']:
            raise ValidationError('Can not send request to self', 'sent_to')


class ContactRequestReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "ContactRequest" filters from request args
    """
    status = fields.String(load_only=True, validate=validate.OneOf(
        CONTACT.CREQ_STATUS_TYPES))
    sender_receiver = fields.String(
        load_only=True, missing=CONTACT.CR_SRT_SEND,
        validate=validate.OneOf(CONTACT.CREQ_SEND_RECV_TYPES))
    full_name = fields.String(load_only=True)
    account_type = fields.String(load_only=True, validate=validate.OneOf(
        ACCOUNT.ACCT_TYPES))
    sector_id = fields.Integer(load_only=True)
    industry_id = fields.Integer(load_only=True)


class ContactRequestEditSchema(ma.Schema):
    """
    Schema for change status by receiver
    """
    status = fields.String(validate=validate.OneOf(
        CONTACT.CREQ_STATUS_TYPES))


class ContactRequestHistorySchema(ma.ModelSchema):
    """
    Schema for contact request history
    """
    class Meta:
        model = ContactRequestHistory
        include_fk = True
