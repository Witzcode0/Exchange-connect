"""
Schemas for "webcast invitees" related models
"""

from marshmallow import fields, validate, validates_schema, ValidationError
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, webcast_fields)
from app.base import constants as APP
from app.webcast_resources.webcast_invitees import (
    constants as WEBCASTINVITEE)
from app.webcast_resources.webcast_invitees.models import WebcastInvitee

user_grp_fields = ['row_id', 'crm_contact_grouped']
invitee_user_fields = user_fields + [
    'email', 'profile.phone_number', 'account.profile.profile_thumbnail_url']

class WebcastInviteeSchema(ma.ModelSchema):
    """
    Schema for loading "webcast invitees" from request,
    and also formatting output
    """

    # default fields to exclude from the schema for speed up
    _default_exclude_fields = ['webcast_invited', ]

    invitee_email = field_for(
        WebcastInvitee, 'invitee_email', field_class=fields.Email,
        validate=[validate.Length(max=WEBCASTINVITEE.INVITEE_EMAIL_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])
    invitee_first_name = field_for(
        WebcastInvitee, 'invitee_first_name',
        validate=[validate.Length(max=WEBCASTINVITEE.INVITEE_NAME_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])
    invitee_last_name = field_for(
        WebcastInvitee, 'invitee_last_name',
        validate=[validate.Length(max=WEBCASTINVITEE.INVITEE_NAME_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])
    invitee_designation = field_for(
        WebcastInvitee, 'invitee_designation',
        validate=[validate.Length(max=WEBCASTINVITEE.INVITEE_DSGN_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = WebcastInvitee
        include_fk = True
        load_only = ('created_by', 'updated_by')
        dump_only = default_exclude + ('created_by', 'updated_by',
                    'is_mail_sent','email_status')
        exclude = ('invitee_j', )

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('webcast_api.webcastinviteeapi', row_id='<row_id>'),
        'collection': ma.URLFor('webcast_api.webcastinviteelistapi')
    }, dump_only=True)

    webcast = ma.Nested(
        'app.webcast_resources.webcasts.schemas.WebcastSchema',
        only=webcast_fields, dump_only=True)

    invitee = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=invitee_user_fields,
        dump_only=True)

    crm_group = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_grp_fields,
        dump_only=True)

    @validates_schema
    def validate_invitee(self, data):
        """
        Validate that not null invitee_id or invitee_email
        """
        error_args = []
        if (('invitee_id' not in data) and ('invitee_email' not in data)):
            error_args = [APP.MSG_NON_EMPTY, 'invitee_id, invitee_email']

        if ('invitee_id' in data and 'invitee_email' in data):
            error_args = ['Both invitee_id and invitee_email' +
                          ' should not be there', 'invitee_id, invitee_email']

        if ('invitee_id' in data and ('invitee_first_name' in data or
                                      'invitee_last_name' in data or
                                      'invitee_designation' in data)):
            error_args = ['If invitee_id is given, invitee_first_name or' +
                          ' invitee_last_name or invitee_designation should'
                          ' not be there',
                          'invitee_id, invitee_first_name, invitee_last_name']

        if error_args:
            raise ValidationError(*error_args)


class WebcastInviteeReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "webcast invitees" filters from request args
    """
    invitee_id = fields.Integer(load_only=True)
    invitee_email = fields.Email(load_only=True)
    webcast_id = fields.Integer(load_only=True)
