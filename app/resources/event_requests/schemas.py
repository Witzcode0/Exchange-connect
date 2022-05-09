"""
Schemas for "event requests" related models (pseudo-models)
"""

from flask import g
from marshmallow import fields, validates_schema, ValidationError
from sqlalchemy import and_

from app import ma
from app.resources.events.models import Event
from app.base.schemas import BaseReadArgsSchema
from app.resources.event_invites.models import EventInvite
from app.resources.event_invites import constants as EVENT_INVITE


class OpenEventJoinSchema(ma.Schema):
    """
    Schema for joining an open event from request
    """
    event_id = fields.Integer()
    _cached_event = None

    @validates_schema
    def validate_event(self, data):
        """
        Validate event_id is present or not, and also checks
        if event is open_to_all or public
        """

        self._cached_event = None
        if 'event_id' in data and data['event_id']:

            # 1. validate event_id
            # make query
            self._cached_event = Event.query.get(data['event_id'])
            if not self._cached_event:
                raise ValidationError(
                    'Event id: %s does not exist' %
                    str(data['event_id']), 'event_id')

            # 2. check event is open to all or public event or neither
            if (not self._cached_event.open_to_all and
                    not self._cached_event.public_event):
                raise ValidationError(
                    'Event id: %s is not open to all or public'
                    % data['event_id'], 'event_id')

            # 3. should not be able to join own event
            if self._cached_event.created_by == g.current_user['row_id']:
                raise ValidationError(
                    'Event id: Can not join own event', 'event_id')


class EventRequestReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "EventInvite" filters from request args
    """
    event_id = fields.Integer(required=True)


class BulkEventInviteStatusChangeSchema(ma.Schema):
    """
    Schema for bulk event invite status change
    """
    invite_ids = fields.List(fields.Integer())
    event_invites = ma.List(ma.Nested(
        'app.resources.event_invites.schemas.EventInviteSchema',
        exclude=['links', 'event_id']))

    @validates_schema(pass_original=True)
    def validate_invite_id_exists(self, data, original_data):
        """
        validate invite id for particular event requested or not
        """
        error = False
        missing = []
        eids = None

        if ('invite_ids' in original_data and original_data['invite_ids'] and
                'event_invites' in original_data and
                original_data['event_invites']):
            raise ValidationError(
                'You can not use %s at same time' %
                'invite_ids, event_invites', 'invite_ids, event_invites'
            )

        if 'invite_ids' in original_data and original_data['invite_ids']:
            eids = original_data['invite_ids'][:]
        if eids:
            # make query
            iids = []
            for iid in eids:
                try:
                    iids.append(int(iid))
                except Exception as e:
                    continue
            query = EventInvite.query.filter(and_(
                EventInvite.row_id.in_(iids),
                EventInvite.status == EVENT_INVITE.REQUESTED))

            invite_ids = []  # for validating missing (incorrect invite ids)
            for c in query.all():
                invite_ids.append(c.row_id)
            missing = set(iids) - set(invite_ids)
            if missing:
                error = True

        if error:
            raise ValidationError(
                'Event Invite: %s do not exist' % missing,
                'invite_ids'
            )
        # when event_invites as list object
        if 'event_invites' in original_data and original_data['event_invites']:
            iids = [event_id['row_id'] for event_id in
                    original_data['event_invites']]

            query = EventInvite.query.filter(EventInvite.row_id.in_(iids))
            invite_ids = []  # for validating missing (incorrect invite ids)
            for c in query.all():
                invite_ids.append(c.row_id)
            missing = set(iids) - set(invite_ids)
            if missing:
                error = True

        if error:
            raise ValidationError(
                'Event Invite: %s do not exist' % missing,
                'event_invites'
            )
