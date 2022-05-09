"""
Schemas for "ca open meeting invitees" related models
"""

from marshmallow import fields

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, ca_open_meeting_fields)
from app.corporate_access_resources.ca_open_meeting_invitees.models \
    import CAOpenMeetingInvitee


# user details that will be passed while populating user relation
invitee_user_fields = user_fields + ['email', 'profile.phone_number']


class CAOpenMeetingInviteeSchema(ma.ModelSchema):
    """
    Schema for loading "ca open meeting invitees" from request,
    and also formatting output
    """

    class Meta:
        model = CAOpenMeetingInvitee
        include_fk = True
        load_only = ('updated_by')
        dump_only = default_exclude + ('created_by', 'updated_by', 'status')
        exclude = ('invitee_j',)

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor(
            'corporate_access_api.caopenmeetinginviteeapi',
            row_id='<row_id>'),
        'collection': ma.URLFor(
            'corporate_access_api.caopenmeetinginviteelistapi')
    }, dump_only=True)

    ca_open_meeting = ma.Nested(
        'app.corporate_access_resources.'
        'ca_open_meetings.schemas.CAOpenMeetingSchema',
        only=ca_open_meeting_fields, dump_only=True)
    invitee = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=invitee_user_fields,
        dump_only=True)


class CAOpenMeetingInviteeReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "ca open meeting invitees filters from request args
    """
    invitee_id = fields.Integer(load_only=True)
    ca_open_meeting_id = fields.Integer(load_only=True)
