"""
Schemas for "result tracker group" related schema
"""
from flask_marshmallow import fields

from app import ma
from app.resources.result_tracker.models import ResultTrackerGroup
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields


class ResultTrackerGroupSchema(ma.ModelSchema):
    """
    Schema for loading data from bse api
    """
    class Meta:
        model = ResultTrackerGroup
        include_fk = True
        load_only = ('updated_by', 'created_by')
        dump_only = default_exclude + ('updated_by', 'created_by')

    users = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)


class ResultTrackerGroupArgsSchema(BaseReadArgsSchema):
    """
        Schema for reading "result tracker group" filters from request args
    """
    # sort_by = fields.List(fields.String(), load_only=True, missing=[
    #     'sequence_id'])
    pass