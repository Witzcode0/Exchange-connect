"""
Schemas for "goal tracker" related models
"""

from marshmallow import (
    fields, validate, validates_schema, ValidationError, pre_dump)
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.resources.goaltrackers.models import GoalTracker
from app.activity.activities import constants as ACTIVITY


class CitySchema(ma.Schema):
    """
    Schema for multiple_cities from request
    """
    country = fields.String()
    city = fields.String()
    target = fields.Integer()


class GoalTrackerSchema(ma.ModelSchema):
    """
    Schema for loading "goaltracker" from request, and also formatting output.
    """

    class Meta:
        model = GoalTracker
        include_fk = True
        load_only = ('deleted', 'created_by', 'account_id',
                     'completed_activity_ids')
        dump_only = ('deleted', 'created_by', 'account_id',
                     'goal_count', 'completed_activity_ids')

    # extra fields for output
    # links = ma.Hyperlinks({
    #     'self': ma.URLFor('api.goaltrackerapi', row_id='<row_id>'),
    #     'collection': ma.URLFor('api.goaltrackerlist')
    # }, dump_only=True)
    # right now being loaded from front-end itself
    """tracked_activities = ma.List(ma.Nested(
        'app.resources.activities.schemas.ActivitySchema',
        only=['row_id', 'subject', 'started_at', 'status']))"""

    activity_types = ma.Nested(
        'app.resources.activity_type.schemas.ActivityTypeSchema',
        only=['row_id','activity_name'])
    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema',  only=user_fields,
        dump_only=True)

    @validates_schema
    def validate_dates(self, data):
        """
        Validate that the started_at and ended_at is valid, i.e started_at <=
        ended_at (same day also possible for daily goals)
        """
        error = False
        started_at = None
        ended_at = None
        if 'started_at' in data:
            started_at = data['started_at']
        else:
            if self.instance:
                # during PUT
                started_at = self.instance.started_at
        if 'ended_at' in data:
            ended_at = data['ended_at']
        else:
            if self.instance:
                # during PUT
                ended_at = self.instance.ended_at

        if started_at and ended_at:
            if started_at > ended_at:
                error = True

        if error:
            raise ValidationError('Date range is incorrect', 'started_at')

    @pre_dump
    def load_activities(self, obj):
        # #TODO: check if activities is there in attributes
        if (hasattr(self, 'tracked_activities') or
                'tracked_activities' in self.fields):
            obj.load_tracked_activities()


class GoalTrackerReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "goal tracker" filters from request args
    """
    # standard db fields
    started_at = fields.DateTime(load_only=True)
    ended_at = fields.DateTime(load_only=True)
    target = fields.Integer(load_only=True)
    goal_name = fields.String(load_only=True)
    activity_name = fields.String(load_only=True)
    activity_type = fields.Integer(load_only=True)

class ActivitiesStatusSchema(ma.Schema):
    """
    schema for activity status update
    """
    completed_ids = fields.List(fields.Integer, required=True)
    incomplete_ids = fields.List(fields.Integer, required=True)

    @validates_schema
    def validate_lists_exclusive(self, data):
        """
        Validate that the lists are mutually exclusive
        """
        error = False
        if 'completed_ids' in data and 'incomplete_ids' in data:
            if not set(data['completed_ids']).isdisjoint(
                    set(data['incomplete_ids'])):
                error = True

        if error:
            raise ValidationError('Lists are overlapping', 'completed_ids')


def validate_tracked_activities(data, obj):
    """
    Validates that the passed ids are actually tracked activities of current
    goal
    """
    total_list = []
    error = {}
    if 'completed_ids' in data and data['completed_ids']:
        total_list.extend(data['completed_ids'])
    if 'incomplete_ids' in data and data['incomplete_ids']:
        total_list.extend(data['incomplete_ids'])

    if total_list and not set(total_list).issubset(set(obj.tracked_ids)):
        error['completed_ids'] = 'Untracked activities passed'
        error['incomplete_ids'] = 'Untracked activities passed'

    return error
