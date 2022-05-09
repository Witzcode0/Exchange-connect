"""
Schemas for "webcast" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, webcast_fields)
from app.base import constants as APP
from app.webcast_resources.webcast_settings.models import WebcastSetting
from app.webcast_resources.webcast_settings import constants as WEBCASTSET


class WebcastSettingSchema(ma.ModelSchema):
    """
    Schema for loading "webcast settings" from request,
    and also formatting output
    """
    welcome_message = field_for(WebcastSetting, 'welcome_message', validate=[
        validate.Length(max=WEBCASTSET.MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    completion_message = field_for(
        WebcastSetting, 'completion_message', validate=[validate.Length(
            max=WEBCASTSET.MAX_LENGTH, error=APP.MSG_LENGTH_EXCEEDS)])
    missed_message = field_for(WebcastSetting, 'missed_message', validate=[
        validate.Length(max=WEBCASTSET.MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = WebcastSetting
        include_fk = True
        load_only = ('updated_by', 'created_by',)
        dump_only = default_exclude + ('updated_by', 'created_by')

    links = ma.Hyperlinks({
        'self': ma.URLFor(
            'webcast_api.webcastsettingapi', row_id='<row_id>'),
        'collection': ma.URLFor('webcast_api.webcastsettinglistapi')
    }, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    webcast = ma.Nested(
        'app.webcast_resources.webcasts.schemas.WebcastSchema', dump_only=True,
        only=webcast_fields)


class WebcastSettingReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "webcast setting" filters from request args
    """
    webcast_id = fields.Integer(load_only=True)
    reminder_1 = fields.DateTime(load_only=True)
    reminder_2 = fields.DateTime(load_only=True)
