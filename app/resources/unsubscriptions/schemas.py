"""
Schemas for "unsubscriptions" related models
"""

from marshmallow import (
    fields, validate, ValidationError, validates_schema)
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.unsubscriptions.models import (
    Unsubscription, UnsubscribeReason)
from app.base import constants as APP


class UnsubscriptionSchema(ma.ModelSchema):
    """
    Schema for loading "unsubscription" from request, and also
    formatting output
    """

    email = field_for(Unsubscription, 'email', field_class=fields.Email)
    events = fields.List(field_for(
        Unsubscription, 'events', validate=validate.OneOf(APP.EVNT_UNSUB_FROM)),
        missing=APP.EVNT_UNSUB_FROM)
    reason = ma.Nested(
        'app.resources.unsubscriptions.schemas.UnsubscribeReasonSchema',
        exclude=default_exclude + ('is_active',), dump_only=True)

    class Meta:
        model = Unsubscription
        include_fk = True
        dump_only = default_exclude + ('email',)


class UnsubscribeReasonSchema(ma.ModelSchema):
    """
    Schema for loading "unsubscribe reason" from request, and also
    formatting output
    """

    title = field_for(UnsubscribeReason, 'title')
    is_active = fields.Boolean(missing=True)

    class Meta:
        model = UnsubscribeReason
        dump_only = default_exclude
        exclude = ['unsubsriptions']


class UnsubscriptionReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "unsubscription" filters from request args
    """
    email = fields.String(load_only=True)
    reason_id = fields.Integer(load_only=True)
    description = fields.String(load_only=True)
    events = fields.String(load_only=True, validate=validate.OneOf(
        APP.EVNT_UNSUB_FROM))


class UnsubscribeReasonReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "unsubscribe reason" filters from request args
    """
    title = fields.String(load_only=True)
    is_active = fields.Boolean(load_only=True)
