"""
Schemas for "user_activity_log" related models
"""
import datetime

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, account_fields)
from app.resources.user_activity_logs.models import UserActivityLog
from app.resources.user_activity_logs import constants as UACTLOG


class UserActivityLogSchema(ma.ModelSchema):
    """
    Schema for loading "user_activity_log" from requests, and also formatting output
    """
    # _default_exclude_fields = ['login_log']
    method = field_for(
        UserActivityLog, 'method', required=True, validate=validate.OneOf(
            ['GET', 'POST', 'PUT', 'DELETE']))

    class Meta:
        model = UserActivityLog
        include_fk = True
        dump_only = default_exclude

    user = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    # relationships
    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema',
        only=account_fields,
        dump_only=True)

    login_log = ma.Nested(
        'app.resources.login_logs.schemas.LoginLogSchema',
        dump_only=True)


class UserActivityLogReadArgsSchema(BaseReadArgsSchema):
    user_id = fields.Integer(load_only=True)
    account_id = fields.Integer(load_only=True)
    created_date = fields.Date(load_only=True)


class UserActivityTimewiseArgsSchema(BaseReadArgsSchema):

    sort_by = fields.List(fields.String(), load_only=True, missing=['created_date'])
    time_unit = fields.String(
        load_only=True, missing=UACTLOG.YEAR,
        validate=validate.OneOf(UACTLOG.TIME_TYPES))
    num_of_bars = fields.Integer(
        load_only=True, missing=10, validate=validate.Range(
            min=1, max=100, error='num_of_bars should be between 1 to 100'))
    date = fields.Date(load_only=True)


class UserActivityTimewiseSchema(ma.Schema):
    time = fields.String(dump_only=True)
    activities = fields.Integer(dump_only=True)
    visits = fields.Integer(dump_only=True)


class UserActivityRecordSchema(ma.Schema):
    """
    Schema to represent list of UserActivityLog
    """
    user_id = fields.Integer(dump_only=True)
    first_name = fields.String(dump_only=True)
    last_name = fields.String(dump_only=True)
    designation = fields.String(dump_only=True)
    account_name = fields.String(dump_only=True)


class UserActivityRecordReadArgSchema(BaseReadArgsSchema):

    sort_by = fields.List(fields.String(), load_only=True, missing=['user_id'])
    user_id = fields.Integer(load_only=True)
    account_id = fields.Integer(load_only=True)
    full_name = fields.String(load_only=True)
    account_name = fields.String(load_only=True)
