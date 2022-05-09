"""
Schemas for "e_meeting invitees" related models
"""

from marshmallow import fields, validate, validates_schema, ValidationError
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, e_meeting_fields)
from app.base import constants as APP
from app.toolkit_resources.project_e_meeting_invitee import constants as MEETINGINVITEE
from app.toolkit_resources.project_e_meeting_invitee.models import (
    EmeetingInvitee)

invitee_fields = user_fields[:] + ['email']
user_grp_fields = ['row_id', 'crm_contact_grouped']


class EmeetingInviteeSchema(ma.ModelSchema):
    """
    Schema for loading "Emeeting invitees" from request,
    and also formatting output
    """

    # default fields to exclude from the schema for speed up

    class Meta:
        model = EmeetingInvitee
        include_fk = True
        load_only = ('created_by', 'updated_by')
        dump_only = default_exclude + (
            'created_by', 'updated_by', 'conference_url')

    e_meeting = ma.Nested(
        'app.toolkit_resources.project_e_meeting.schemas.EMeetingSchema',
        only=e_meeting_fields, dump_only=True)

    invitee = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=invitee_fields,
        dump_only=True)

    @validates_schema
    def validate_invitee(self, data):
        """
        Multiple validation checks for invitee_id, invitee_email,
        invitee_first_name, invitee_last_name and invitee_designation
        """
        error_args = []
        if ('invitee_id' not in data):
            error_args = [APP.MSG_NON_EMPTY, 'invitee_id']

        if error_args:
            raise ValidationError(*error_args)
