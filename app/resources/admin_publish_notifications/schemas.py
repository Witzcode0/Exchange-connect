"""
Schemas for "admin publish notifications" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.admin_publish_notifications.models import \
    AdminPublishNotification
from app.resources.accounts import constants as ACCOUNT


class AdminPublishNotificationSchema(ma.ModelSchema):
    """
    Schema for loading "countries" from requests, and also formatting output
    """
    _default_exclude_fields = []
    account_type_preference = fields.List(field_for(
        AdminPublishNotification, 'account_type_preference',
        validate=validate.OneOf(ACCOUNT.ACCT_TYPES)))

    class Meta:
        model = AdminPublishNotification
        include_fk = True
        load_only = ('updated_by', 'created_by')
        dump_only = default_exclude + ('updated_by', 'created_by')

    # links = ma.Hyperlinks({
    #     'self': ma.URLFor('api.countryapi', row_id='<row_id>'),
    #     'collection': ma.URLFor('api.countrylistapi')
    # }, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=[
            'row_id', 'account_id'], dump_only=True)


class AdminPublishNotificationReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "countries" filters from request args
    """

    title = fields.String(load_only=True)
    account_type_preference = fields.String(
        load_only=True, validate=validate.OneOf(ACCOUNT.ACCT_TYPES))
