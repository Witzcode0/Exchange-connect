"""
Schemas for "event invite" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base import constants as APP
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.resources.event_invites import constants as EVENT_INVITE
from app.resources.event_invites.models import EventInvite


invite_user_fields = user_fields + ['email', 'profile.phone_number']


class EventInviteSchema(ma.ModelSchema):
    """
    Schema for loading "EventInvite" from request, and also
    formatting output
    """

    status = field_for(EventInvite, 'status', validate=validate.OneOf(
        EVENT_INVITE.EVT_INV_STATUS_TYPES))
    comment = field_for(EventInvite, 'comment', validate=[
        validate.Length(max=EVENT_INVITE.COMMENT_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = EventInvite
        include_fk = True
        load_only = ('deleted', 'updated_by', 'created_by')
        dump_only = default_exclude + ('updated_by', 'deleted', 'created_by')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.eventinviteapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.eventinviteslistapi')
    })

    invitee = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=invite_user_fields,
        dump_only=True)
    event = ma.Nested(
        'app.resources.events.schemas.EventSchema', dump_only=True)


class EventInviteReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "EventInvite" filters from request args
    """
    # standard db fields

    status = fields.String(load_only=True, validate=validate.OneOf(
        EVENT_INVITE.EVT_INV_STATUS_TYPES))

    event_id = fields.Integer(load_only=True)
    user_id = fields.Integer(load_only=True)

    updated_by = fields.Integer(load_only=True)
    created_by = fields.Integer(load_only=True)
