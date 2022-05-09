"""
Schemas for "webinar hosts" related models
"""

from marshmallow import fields, validate, validates_schema, ValidationError
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base import constants as APP
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, webinar_fields)
from app.webinar_resources.webinar_hosts.models import WebinarHost
from app.webinar_resources.webinar_hosts import constants as WEBINARHOST


class WebinarHostSchema(ma.ModelSchema):
    """
    Schema for loading "webinar hosts" from request,
    and also formatting output
    """

    # default fields to exclude from the schema for speed up
    _default_exclude_fields = ['webinar', ]

    host_email = field_for(
        WebinarHost, 'host_email', field_class=fields.Email,
        validate=[validate.Length(
            max=WEBINARHOST.HOST_EMAIL_MAX_LENGTH,
            error=APP.MSG_LENGTH_EXCEEDS)])
    host_first_name = field_for(
        WebinarHost, 'host_first_name', validate=[
            validate.Length(max=WEBINARHOST.HOST_NAME_MAX_LENGTH,
                            error=APP.MSG_LENGTH_EXCEEDS)])
    host_last_name = field_for(
        WebinarHost, 'host_last_name', validate=[
            validate.Length(max=WEBINARHOST.HOST_NAME_MAX_LENGTH,
                            error=APP.MSG_LENGTH_EXCEEDS)])
    host_designation = field_for(
        WebinarHost, 'host_designation', validate=[
            validate.Length(max=WEBINARHOST.HOST_DESIGNATION_MAX_LENGTH,
                            error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = WebinarHost
        include_fk = True
        load_only = ('created_by', 'updated_by')
        dump_only = default_exclude + ('created_by', 'updated_by',
            'conference_url', 'is_mail_sent', 'email_status')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('webinar_api.webinarhostapi', row_id='<row_id>'),
        'collection': ma.URLFor('webinar_api.webinarhostlistapi')
    }, dump_only=True)

    webinar = ma.Nested(
        'app.webinar_resources.webinars.schemas.WebinarSchema',
        only=webinar_fields, dump_only=True)

    host = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)

    @validates_schema
    def validate_host(self, data):
        """
        Multiple validation checks for host_id, host_email,
        host_first_name, host_last_name and host_designation
        """
        error_args = []
        if ('host_id' not in data and 'host_email' not in data):
            error_args = [APP.MSG_NON_EMPTY, 'host_id, host_email']

        if ('host_id' in data and 'host_email' in data):
            error_args = ['Both host_id and host_email' +
                          ' should not be there', 'host_id, host_email']

        if ('host_id' in data and (
                'host_first_name' in data or
                'host_last_name' in data or 'host_designation' in data)):
            error_args = [
                'If host_id is given, host_first_name, host_last_name ' +
                'and host_designation should not be there', 'host_id, ' +
                'host_first_name, host_last_name, host_designation']

        if error_args:
            raise ValidationError(*error_args)


class WebinarHostReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "webinar hosts" filters from request args
    """
    host_id = fields.Integer(load_only=True)
    webinar_id = fields.Integer(load_only=True)
    host_email = fields.Email(load_only=True)
