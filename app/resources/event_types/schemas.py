"""
Schemas for "event type" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base import constants as APP
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.event_types.models import EventType
from app.resources.event_types import constants as EVENT_TYPE


class EventTypeSchema(ma.ModelSchema):
    """
    Schema for loading "Event Type" from request, and also formatting output
    """

    name = field_for(EventType, 'name', validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=EVENT_TYPE.NAME_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = EventType
        include_fk = True
        load_only = ('deleted', 'updated_by', 'created_by', 'account_id')
        dump_only = default_exclude + (
            'updated_by', 'deleted', 'created_by', 'account_id')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.eventtypeapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.eventtypelistapi')
    }, dump_only=True)


class EventTypeReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "Event Type" filters from request args
    """
    name = fields.String(load_only=True)
