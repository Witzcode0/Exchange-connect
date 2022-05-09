"""
Schemas for "reference event types" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, account_fields)
from app.base import constants as APP
from app.corporate_access_resources.ref_event_types import (
    constants as CAREF_EVENT_TYPES)
from app.corporate_access_resources.ref_event_types.models import \
    CARefEventType


class CARefEventTypeSchema(ma.ModelSchema):
    """
    Schema for loading "reference event types" from request,
    and also formatting output
    """
    # default fields to exclude from the schema for speed up
    _default_exclude_fields = [
        'corporate_access_events', 'corporate_access_ref_event_sub_types',
        'ca_open_meetings', ]

    name = field_for(CARefEventType, 'name', validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=CAREF_EVENT_TYPES.NAME_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    description = field_for(CARefEventType, 'description', validate=[
        validate.Length(max=CAREF_EVENT_TYPES.DESCRIPTION_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = CARefEventType
        include_fk = True
        load_only = ('created_by', 'updated_by', 'deleted')
        dump_only = default_exclude + (
            'created_by', 'updated_by', 'deleted')

    links = ma.Hyperlinks(
        {'self': ma.URLFor(
            'corporate_access_api.carefeventtypeapi', row_id='<row_id>'),
         'collection': ma.URLFor(
            'corporate_access_api.carefeventtypelistapi')},
        dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)


class CARefEventTypeReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "reference event types" filters from request args
    """
    name = fields.String(load_only=True)
    is_meeting = fields.Boolean(load_only=True)
