"""
Schemas for "states" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base import constants as APP
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.states.models import State
from app.resources.states import constants as STATE


class StateSchema(ma.ModelSchema):
    """
    Schema for loading "states" from requests, and also formatting output
    """

    # default fields to exclude from the schema for speed up
    _default_exclude_fields = ['corporate_access_events']

    state_name = field_for(State, 'state_name', validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=STATE.STATE_NAME_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = State
        include_fk = True
        load_only = ('updated_by', 'created_by', 'deleted')
        dump_only = default_exclude + ('updated_by', 'created_by', 'deleted')

    links = ma.Hyperlinks({
        'self': ma.URLFor('api.stateapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.statelistapi')
    }, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=['row_id'],
        dump_only=True)


class StateReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "states" filters from request args
    """

    state_name = fields.String(load_only=True)
    country_id = fields.Integer(load_only=True)
