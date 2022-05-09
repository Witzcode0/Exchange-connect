"""
Schemas for "login_log" related models
"""

from marshmallow import fields

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.resources.login_logs.models import LoginLog


class LoginLogSchema(ma.ModelSchema):
    """
    Schema for loading "login_log" from requests, and also formatting output
    """

    class Meta:
        model = LoginLog
        include_fk = True
        dump_only = default_exclude

    # relationships
    user = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)


class LoginLogReadArgsSchema(BaseReadArgsSchema):
    user_id = fields.Integer(load_only=True, required=True)
