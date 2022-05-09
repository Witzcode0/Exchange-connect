"""
Schemas for "corporate access event hosts" related models
"""

from marshmallow import fields, validates_schema, ValidationError

from app import ma
from app.base import constants as APP
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, ca_event_fields)
from app.corporate_access_resources.corporate_access_event_hosts.models \
    import CorporateAccessEventHost


class CorporateAccessEventHostSchema(ma.ModelSchema):
    """
    Schema for loading "corporate_access_event hosts" from request,
    and also formatting output
    """

    class Meta:
        model = CorporateAccessEventHost
        include_fk = True
        load_only = ('created_by', 'updated_by')
        dump_only = default_exclude + ('created_by', 'updated_by',
            'is_mail_sent','email_status')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('corporate_access_api.corporateaccesseventhostapi',
                          row_id='<row_id>'),
        'collection': ma.URLFor(
            'corporate_access_api.corporateaccesseventhostlistapi')
    }, dump_only=True)

    host = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)

    corporate_access_event = ma.Nested(
        'app.corporate_access_resources.'
        'corporate_access_events.schemas.CorporateAccessEventSchema',
        only=ca_event_fields, dump_only=True)

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
        if 'host_id' not in data and 'host_email' not in data:
            error_args = [APP.MSG_NON_EMPTY, 'host_id, host_email']

        if 'host_id' in data and 'host_email' in data:
            error_args = ['Both host_id and host_email' +
                          ' should not be there', 'host_id, host_email']

        if ('host_id' in data and (
                            'host_first_name' in data or
                            'host_last_name' in data or
                            'host_designation' in data)):
            error_args = [
                'If host_id is given, host_first_name, ' +
                'host_last_name and host_designation ' +
                'should not be there', 'host_id, host_first_name, ' +
                'host_last_name, host_designation']

        if error_args:
            raise ValidationError(*error_args)


class CorporateAccessEventHostReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "corporate_access_event hosts" filters from request args
    """
    host_id = fields.Integer(load_only=True)
    corporate_access_event_id = fields.Integer(load_only=True)
