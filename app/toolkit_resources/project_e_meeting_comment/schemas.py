"""
Schemas for "Emeeting Comment" related models
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
from app.toolkit_resources.project_e_meeting_comment.models import (
    EmeetingComment)
from app.toolkit_resources.project_e_meeting_comment import constants as COMMENT
from app.toolkit_resources.projects.models import (
    Project)


# account details that will be passed while populating account relation
account_fields = ['row_id', 'links', 'account_name', 'account_type',
                  'profile.profile_thumbnail_url']
# account details that will be passed while populating account relation
creator_user_fields = user_fields[:] + [
    'account.profile.profile_thumbnail_url']


class EMeetingCommentSchema(ma.ModelSchema):
    """
    Schema for loading "Emeeting" from request,\
    and also formatting output
    """

    _default_exclude_fields = ['e_meeting']

    status = field_for(
        EmeetingComment, 'status', validate=validate.OneOf(
            COMMENT.E_MEETING_STATUS_TYPES))

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=creator_user_fields,
        dump_only=True)

    meeting = ma.Nested(
        'app.toolkit_resources.project_e_meeting.schemas.EMeetingSchema',
        dump_only=True)

    class Meta:
        model = EmeetingComment
        include_fk = True
        load_only = ('updated_by', 'created_by', 'meeting_datetime')
        dump_only = default_exclude + \
            ('created_by', 'updated_by', 'meeting_datetime')

    # @validates_schema(pass_original = True)
    def validate_started_at(self, data, original_data):
        """
        Validate meeting_datetime with today date(ended_at greater then started_at)
        """
        if original_data['status'] == COMMENT.RESCHEDULE:
            error = False
            if ('meeting_datetime' not in original_data):
                raise ValidationError(
                    'Please provide start date and time', 'meeting_datetime')
            elif ('meeting_datetime' in original_data):
                datetimeFormat = '%Y-%m-%d %H:%M:%S'
                now = datetime.datetime.now()

                duration = datetime.datetime.strptime(
                    str(original_data['meeting_datetime']), datetimeFormat)
                - datetime.datetime.now()

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


class EmeetingCommentReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "e_meeting" filters from request args
    """
    comment = fields.String(load_only=True)
    status = fields.String(load_only=True)
    e_meeting_id = fields.Integer(load_only=True, required=True)
    # modified date fields
    meeting_datetime = fields.DateTime(load_only=True)
