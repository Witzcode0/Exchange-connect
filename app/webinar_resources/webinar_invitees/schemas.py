"""
Schemas for "webinar invitees" related models
"""

from marshmallow import fields, validate, validates_schema, ValidationError
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, webinar_fields)
from app.base import constants as APP
from app.webinar_resources.webinar_invitees import constants as WEBINARINVITEE
from app.webinar_resources.webinar_invitees.models import WebinarInvitee

invitee_fields = user_fields[:] + ['email']
user_grp_fields = ['row_id', 'crm_contact_grouped']


class WebinarInviteeSchema(ma.ModelSchema):
    """
    Schema for loading "webinar invitees" from request,
    and also formatting output
    """

    # default fields to exclude from the schema for speed up
    _default_exclude_fields = ['webinar', ]

    invitee_email = field_for(
        WebinarInvitee, 'invitee_email', field_class=fields.Email,
        validate=[validate.Length(
            max=WEBINARINVITEE.INVITEE_EMAIL_MAX_LENGTH,
            error=APP.MSG_LENGTH_EXCEEDS)])
    invitee_first_name = field_for(
        WebinarInvitee, 'invitee_first_name', validate=[
            validate.Length(max=WEBINARINVITEE.INVITEE_NAME_MAX_LENGTH,
                            error=APP.MSG_LENGTH_EXCEEDS)])
    invitee_last_name = field_for(
        WebinarInvitee, 'invitee_last_name', validate=[
            validate.Length(max=WEBINARINVITEE.INVITEE_NAME_MAX_LENGTH,
                            error=APP.MSG_LENGTH_EXCEEDS)])
    invitee_designation = field_for(
        WebinarInvitee, 'invitee_designation', validate=[
            validate.Length(max=WEBINARINVITEE.INVITEE_DESIGNATION_MAX_LENGTH,
                            error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = WebinarInvitee
        include_fk = True
        load_only = ('created_by', 'updated_by')
        dump_only = default_exclude + (
            'created_by', 'updated_by', 'conference_url', 'status',
            'is_mail_sent','email_status')
        exclude = ('invitee_j',)

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('webinar_api.webinarinviteeapi', row_id='<row_id>'),
        'collection': ma.URLFor('webinar_api.webinarinviteelistapi')
    }, dump_only=True)

    webinar = ma.Nested(
        'app.webinar_resources.webinars.schemas.WebinarSchema',
        only=webinar_fields, dump_only=True)

    invitee = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=invitee_fields,
        dump_only=True)

    crm_group = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_grp_fields,
        dump_only=True)

    @validates_schema
    def validate_invitee(self, data):
        """
        Multiple validation checks for invitee_id, invitee_email,
        invitee_first_name, invitee_last_name and invitee_designation
        """
        error_args = []
        if ('invitee_id' not in data and 'invitee_email' not in data):
            error_args = [APP.MSG_NON_EMPTY, 'invitee_id, invitee_email']

        if ('invitee_id' in data and 'invitee_email' in data):
            error_args = ['Both invitee_id and invitee_email' +
                          ' should not be there', 'invitee_id, invitee_email']

        if ('invitee_id' in data and (
                'invitee_first_name' in data or
                'invitee_last_name' in data or 'invitee_designation' in data)):
            error_args = [
                'If invitee_id is given, invitee_first_name, ' +
                'invitee_last_name and invitee_designation ' +
                'should not be there', 'invitee_id, invitee_first_name, ' +
                'invitee_last_name, invitee_designation']

        if error_args:
            raise ValidationError(*error_args)


class WebinarInviteeReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "webinar invitees" filters from request args
    """
    invitee_id = fields.Integer(load_only=True)
    invitee_email = fields.Email(load_only=True)
    webinar_id = fields.Integer(load_only=True)
