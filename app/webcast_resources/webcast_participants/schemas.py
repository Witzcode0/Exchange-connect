"""
Schemas for "webcast participants" related models
"""

from flask import g
from marshmallow import fields, validate, validates_schema, ValidationError
from marshmallow_sqlalchemy import field_for
from sqlalchemy.orm import load_only
from sqlalchemy import and_, or_

from app import ma
from app.base import constants as APP
from app.webcast_resources.webcast_participants import constants as WEBPART
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, webcast_fields)
from app.webcast_resources.webcast_participants.models import (
    WebcastParticipant)
from app.resources.users.models import User


class WebcastParticipantSchema(ma.ModelSchema):
    """
    Schema for loading "webcast participant" from request,
    and also formatting output
    """

    # default fields to exclude from the schema for speed up
    _default_exclude_fields = ['webcast_participated', ]

    participant_email = field_for(
        WebcastParticipant, 'participant_email', field_class=fields.Email,
        validate=[validate.Length(max=WEBPART.PRTCPNT_EMAIL_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])
    participant_first_name = field_for(
        WebcastParticipant, 'participant_first_name',
        validate=[validate.Length(max=WEBPART.PRTCPNT_NAME_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])
    participant_last_name = field_for(
        WebcastParticipant, 'participant_last_name',
        validate=[validate.Length(max=WEBPART.PRTCPNT_NAME_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])
    participant_designation = field_for(
        WebcastParticipant, 'participant_designation',
        validate=[validate.Length(max=WEBPART.PRTCPNT_DSGN_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])
    sequence_id = field_for(
        WebcastParticipant, 'sequence_id', validate=validate.Range(
            min=APP.SEQUENCE_ID_MIN_VALUE,
            error=APP.SEQUENCE_ID_MIN_VALUE_ERROR))

    class Meta:
        model = WebcastParticipant
        include_fk = True
        load_only = ('updated_by', 'created_by',)
        dump_only = default_exclude + ('updated_by', 'created_by',
                    'is_mail_sent','email_status')

    links = ma.Hyperlinks({
        'self': ma.URLFor(
            'webcast_api.webcastparticipantapi', row_id='<row_id>'),
        'collection': ma.URLFor('webcast_api.webcastparticipantlistapi')
    }, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    participant = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    webcast = ma.Nested(
        'app.webcast_resources.webcasts.schemas.WebcastSchema', dump_only=True,
        only=webcast_fields)

    @validates_schema(pass_original=True)
    def validate_participant_user(self, data, original_data):
        """
        Validate the participant id which is exists or not in user and hold
        same account of Webcast creator
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

    @validates_schema
    def validate_participant(self, data):
        """
        Validate that not null participant_id or participant_email
        """
        error_args = []
        if ('participant_id' not in data and 'participant_email' not in data):
            error_args = [APP.MSG_NON_EMPTY,
                          'participant_id, participant_email']

        if ('participant_id' in data and 'participant_email' in data):
            error_args = ['Both participant_id and participant_email' +
                          ' should not be there', 'participant_id,' +
                          ' participant_email']

        if ('participant_id' in data and ('participant_first_name' in data or
                                          'participant_last_name' in data or
                                          'participant_designation' in data)):
            error_args = ['If participant_id is given, ' +
                          'participant_first_name or participant_last_name,' +
                          'or participant_designation should'
                          ' not be there',
                          'participant_id, participant_first_name,' +
                          'participant_last_name']

        if error_args:
            raise ValidationError(*error_args)


class WebcastParticipantReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "webcast participant" filters from request args
    """
    webcast_id = fields.Integer(load_only=True)
    participant_id = fields.Integer(load_only=True)
    participant_email = fields.Email(load_only=True)
