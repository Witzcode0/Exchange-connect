"""
Schemas for "ref event sub types" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (default_exclude, BaseReadArgsSchema, user_fields,
                              account_fields)
from app.base import constants as APP
from app.corporate_access_resources.ref_event_sub_types import constants \
    as REFEVE_SUBTYPE
from app.corporate_access_resources.ref_event_sub_types.models \
    import CARefEventSubType


class CARefEventSubTypeSchema(ma.ModelSchema):
    """
    Schema for loading "ref event sub types" from request,
    and also formatting output
    """
    # default fields to exclude from the schema for speed up
    _default_exclude_fields = [
        'corporate_access_events', 'corporate_access_ref_event_sub_types',
        'ca_open_meetings', ]

    name = field_for(CARefEventSubType, 'name', validate=[validate.Length(
                     min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=REFEVE_SUBTYPE.NAME_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    description = field_for(CARefEventSubType, 'description',
                            validate=[validate.Length(
                                max=REFEVE_SUBTYPE.DESC_MAX_LENGTH,
                                error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = CARefEventSubType
        include_fk = True
        load_only = ('updated_by', 'created_by', 'deleted')
        dump_only = default_exclude + ('updated_by', 'created_by', 'deleted')

    links = ma.Hyperlinks({
        'self': ma.URLFor(
            'corporate_access_api.carefeventsubtypeapi', row_id='<row_id>'),
        'collection': ma.URLFor(
            'corporate_access_api.carefeventsubtypelistapi')
    }, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    event_type = ma.Nested(
        'app.corporate_access_resources.'
        'ref_event_types.schemas.CARefEventTypeSchema', dump_only=True,
        exclude=_default_exclude_fields)


class CARefEventSubTypeEditSchema(CARefEventSubTypeSchema):
    """
    Schema for loading "ref event sub types" from put request,
    and also formatting output
    """

    class Meta:
        dump_only = default_exclude + ('updated_by', 'created_by', 'deleted',
                                       'has_slots')


class CARefEventSubTypeReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "ref event sub types" filters from request args
    """
    event_type_id = fields.Integer(load_only=True)
    name = fields.String(load_only=True)
    is_meeting = fields.Boolean(load_only=True)
