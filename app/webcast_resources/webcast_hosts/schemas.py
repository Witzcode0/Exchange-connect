"""
Schemas for "webcast hosts" related models
"""

from marshmallow import fields, validate, validates_schema, ValidationError
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base import constants as APP
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, webcast_fields)
from app.webcast_resources.webcast_hosts import constants as WEBCASTHOST
from app.webcast_resources.webcast_hosts.models import WebcastHost


class WebcastHostSchema(ma.ModelSchema):
    """
    Schema for loading "webcast hosts" from request,
    and also formatting output
    """

    # default fields to exclude from the schema for speed up
    _default_exclude_fields = ['webcast_hosted', ]

    host_email = field_for(
        WebcastHost, 'host_email', field_class=fields.Email,
        validate=[validate.Length(max=WEBCASTHOST.HOST_EMAIL_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])
    host_first_name = field_for(
        WebcastHost, 'host_first_name',
        validate=[validate.Length(max=WEBCASTHOST.HOST_NAME_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])
    host_last_name = field_for(
        WebcastHost, 'host_last_name',
        validate=[validate.Length(max=WEBCASTHOST.HOST_NAME_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])
    host_designation = field_for(
        WebcastHost, 'host_designation',
        validate=[validate.Length(max=WEBCASTHOST.HOST_DSGN_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = WebcastHost
        include_fk = True
        load_only = ('created_by', 'updated_by')
        dump_only = default_exclude + ('created_by', 'updated_by',
                    'is_mail_sent','email_status')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('webcast_api.webcasthostapi', row_id='<row_id>'),
        'collection': ma.URLFor('webcast_api.webcasthostlistapi')
    }, dump_only=True)

    webcast = ma.Nested(
        'app.webcast_resources.webcasts.schemas.WebcastSchema',
        only=webcast_fields, dump_only=True)

    host = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)

    @validates_schema
    def validate_host(self, data):
        """
        Validate that not null host_id or host_email
        """
        error_args = []
        if (('host_id' not in data) and ('host_email' not in data)):
            error_args = [APP.MSG_NON_EMPTY, 'host_id, host_email']

        if ('host_id' in data and 'host_email' in data):
            error_args = ['Both host_id and host_email' +
                          ' should not be there', 'host_id, host_email']

        if ('host_id' in data and ('host_first_name' in data or
                                   'host_last_name' in data or
                                   'host_designation' in data)):
            error_args = ['If host_id is given, host_first_name or' +
                          ' host_last_name or host_designation should'
                          ' not be there',
                          'host_id, host_first_name, host_last_name']

        if error_args:
            raise ValidationError(*error_args)


class WebcastHostReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "webcast hosts" filters from request args
    """
    host_id = fields.Integer(load_only=True)
    webcast_id = fields.Integer(load_only=True)
    host_email = fields.Email(load_only=True)
