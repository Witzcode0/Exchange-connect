"""
Schemas for "ca open meeting participants" related models
"""

from flask import g
from marshmallow import fields, validates_schema, ValidationError, validate
from marshmallow_sqlalchemy import field_for
from sqlalchemy import and_, or_
from sqlalchemy.orm import load_only

from app import ma
from app.base import constants as APP
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, ca_open_meeting_fields)
from app.corporate_access_resources.ca_open_meeting_participants.models \
    import CAOpenMeetingParticipant
from app.resources.users.models import User


class CAOpenMeetingParticipantSchema(ma.ModelSchema):
    """
    Schema for loading "ca open meeting participant" from request,
    and also formatting output
    """
    sequence_id = field_for(
        CAOpenMeetingParticipant, 'sequence_id',
        validate=validate.Range(
            min=APP.SEQUENCE_ID_MIN_VALUE,
            error=APP.SEQUENCE_ID_MIN_VALUE_ERROR))

    class Meta:
        model = CAOpenMeetingParticipant
        include_fk = True
        load_only = ('updated_by', 'created_by',)
        dump_only = default_exclude + ('updated_by', 'created_by',)

    links = ma.Hyperlinks({
        'self': ma.URLFor(
            'corporate_access_api.caopenmeetingparticipantapi',
            row_id='<row_id>'),
        'collection': ma.URLFor(
            'corporate_access_api.caopenmeetingparticipantlistapi')
    }, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    participant = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    ca_open_meeting = ma.Nested(
        'app.corporate_access_resources.'
        'ca_open_meetings.schemas.CAOpenMeetingSchema',
        only=ca_open_meeting_fields, dump_only=True)

    @validates_schema
    def validate_participant(self, data):
        """
        Multiple validation checks for participant_id, participant_email,
        participant_first_name, participant_last_name and
        participant_designation
        """
        error_args = []
        if 'participant_id' not in data and 'participant_email' not in data:
            error_args = [APP.MSG_NON_EMPTY,
                          'participant_id, participant_email']

        if 'participant_id' in data and 'participant_email' in data:
            error_args = ['Both participant_id and participant_email' +
                          ' should not be there', 'participant_id, '
                                                  'participant_email']

        if ('participant_id' in data and (
                'participant_first_name' in data or
                'participant_last_name' in data or
                'participant_designation' in data)):
            error_args = [
                'If participant_id is given, participant_first_name, ' +
                'participant_last_name and participant_designation ' +
                'should not be there', 'participant_id, '
                                       'participant_first_name, ' +
                'participant_last_name, participant_designation']

        if error_args:
            raise ValidationError(*error_args)

    @validates_schema(pass_original=True)
    def validate_participant_user(self, data, original_data):
        """
        Validate the participant id which is exists or not in user and hold
        same account of meeting creator
        """
        error = False
        user_data = None
        if ('participant_id' in original_data and
                original_data['participant_id']):
            # if event created by group account user so participant
            # will be both account team member(child or group)
            user_data = User.query.filter(and_(
                User.row_id == original_data['participant_id'], or_(
                    User.account_id == g.current_user['primary_account_id'],
                    User.account_id == g.current_user['account_id']))).options(
                load_only('row_id', 'account_id')).first()
            if not user_data:
                error = True
        if error:
            raise ValidationError(
                'User: %s do not exist' % original_data['participant_id'],
                'participant_id'
            )


class CAOpenMeetingParticipantReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "ca open meeting participant" filters from request args
    """
    ca_open_meeting_id = fields.Integer(load_only=True)
    participant_id = fields.Integer(load_only=True)
