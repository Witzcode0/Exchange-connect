"""
Schemas for "cities" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base import constants as APP
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.activity_type.models import ActivityType


class ActivityTypeSchema(ma.ModelSchema):
    """
    Schema for loading "ActivityType" from requests, and also formatting output
    """
    _default_exclude_fields = ['deleted']

    class Meta:
        model = ActivityType
        include_fk = True
        load_only = ('updated_by', 'created_by')
        dump_only = ('updated_by', 'created_by')

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=['row_id'],
        dump_only=True)


class ActivityTypeReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "ActivityType" filters from request args
    """
    # standard db fields
    sort_by = fields.List(fields.String(), load_only=True, missing=['created_date'])

