"""
Schemas for "Emeeting" related models
"""

import datetime
import time
from marshmallow import (
    fields, validate, pre_dump, validates_schema, ValidationError, pre_load)
from marshmallow_sqlalchemy import field_for
from sqlalchemy import and_, or_
from flask import g
from sqlalchemy.orm import load_only, joinedload

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.base import constants as APP
from app.toolkit_resources.project_e_meeting.models import (
    Emeeting)
from app.toolkit_resources.project_e_meeting import constants as MEETING
from app.toolkit_resources.project_e_meeting_invitee.schemas import (
    EmeetingInviteeSchema)
from app.toolkit_resources.projects.models import (
    Project)


# account details that will be passed while populating account relation
account_fields = ['row_id', 'links', 'account_name', 'account_type',
                  'profile.profile_thumbnail_url']
# account details that will be passed while populating account relation
creator_user_fields = user_fields[:] + [
    'account.profile.profile_thumbnail_url']


class EMeetingSchema(ma.ModelSchema):
    """
    Schema for loading "Emeeting" from request,\
    and also formatting output
    """
    _default_exclude_fields = ['invitees']

    meeting_subject = field_for(Emeeting, 'meeting_subject', validate=[
        validate.Length(max=MEETING.COMMON_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    meeting_agenda = field_for(Emeeting, 'meeting_agenda', validate=[
        validate.Length(max=MEETING.AGENDA_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])

    invitee_ids = fields.List(fields.Integer(), dump_only=True)

    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True)
    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=creator_user_fields,
        dump_only=True)

    invited = ma.Nested('EmeetingInviteeSchema',
                        only=['e_meeting_id', 'invitee_id', 'row_id',
                              'conference_url', 'invitee_email'],
                        dump_only=True)

    e_meeting_invitees = ma.List(ma.Nested('EmeetingInviteeSchema',
                                           only=['e_meeting_id', 'invitee_id',
                                                 'row_id', 'invitee_email',
                                                 'modified_date',
                                                 'conference_url',
                                                 'invitee'],
                                           dump_only=True))

    invitee_ids = fields.List(fields.Integer(), dump_only=True)

    class Meta:
        model = Emeeting
        include_fk = True
        load_only = ('updated_by', 'created_by', 'account_id')
        dump_only = default_exclude + \
            ('created_by', 'updated_by', 'admin_url', 'account_id')

    # @validates_schema
    def validate_started_at(self, data):
        """
        Validate meeting_datetime with today date(ended_at greater then started_at)
        """
        error = False
        if ('meeting_datetime' not in data):
            raise ValidationError(
                'Please provide start date and time', 'meeting_datetime')
        elif ('meeting_datetime' in data):
            datetimeFormat = '%Y-%m-%d %H:%M:%S'
            now = datetime.datetime.now()
            meeting_datetime = str(data['meeting_datetime']).split(' ')

            if '+' in meeting_datetime[1]:
                meeting_datetime_timezone = meeting_datetime[1].split('+')[0]
            if '-' in meeting_datetime[1]:
                meeting_datetime_timezone = meeting_datetime[1].split('-')[0]

            meeting_datetime = meeting_datetime[0] + \
                ' ' + meeting_datetime_timezone
            duration = datetime.datetime.strptime(
                meeting_datetime, datetimeFormat) - datetime.datetime.now()

            days = int((str(duration).split(',')[0]).split(
                ' ')[0]) if 'days' in str(duration) else 0

            if ',' in str(duration):
                duration_time = datetime.datetime.strptime(
                    str(duration).split(',')[1].strip(), "%H:%M:%S.%f")
            else:
                duration_time = datetime.datetime.strptime(
                    str(duration), "%H:%M:%S.%f")

            duration_time = duration_time - datetime.datetime(1900, 1, 1)
            duration_seconds = duration_time.total_seconds() + 86400*days

            if duration_seconds < 900:
                raise ValidationError(
                    'Invalid Meeting Datetime')

    @validates_schema(pass_original=True)
    def validate_invitee_ids(self, data, original_data):
        """
        Validate the Invitee_id exist
        """
        error_invt = False  # flag for invitee_ids error
        error_pr = False  # flag for project_id error
        missing_invt = []  # list for invalid invitee_ids
        remaining_iids_invt = None
        project_id_query = None
        self._cached_project_users = []  # for invitee_ids valid user
        eids_invt = []  # for invitees
        if 'invitee_ids' in original_data and original_data['invitee_ids']:
            eids_invt = original_data['invitee_ids'][:]
        if eids_invt:
            # make query
            iids_invt = []
            for iid in eids_invt:
                try:
                    iids_invt.append(int(iid))
                    self._cached_project_users.append(iid)
                except Exception as e:
                    continue

            if 'project_id' in original_data:
                query = Project.query.filter(
                    Project.row_id == original_data['project_id']).first()

                if not query:
                    project_id_query = original_data['project_id']
                    error_pr = True

                if query:
                    invitee_ids = []
                    # for validating missing (incorrect user ids)
                    the_invitees = query.analysts + query.designers + [query.creator]

                    # self._cached_project_users.append(the_analysts)
                    if the_invitees:
                        for invitee_id in the_invitees:
                            invitee_ids.append(invitee_id.row_id)

                    remaining_iids_invt = set(iids_invt) - set(invitee_ids)
                    if remaining_iids_invt:
                        error_invt = True

        if error_pr:
            if project_id_query:
                raise ValidationError(
                    'Emetting: %s do not exist' % project_id_query)

        if error_invt:
            if remaining_iids_invt:
                raise ValidationError(
                    'Emetting: %s do not exist' % remaining_iids_invt,
                    'invitee_ids'
                )


class EmeetingReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "e_meeting" filters from request args
    """
    meeting_subject = fields.String(load_only=True)
    meeting_agenda = fields.String(load_only=True)
    cancelled = fields.String(load_only=True)
    project_id = fields.Integer(load_only=True, required=True)
    main_filter = fields.String(load_only=True, validate=validate.OneOf(
        MEETING.MEETING_LISTS))
    # modified date fields
    meeting_datetime_from = fields.DateTime(load_only=True)
    meeting_datetime_to = fields.DateTime(load_only=True)
