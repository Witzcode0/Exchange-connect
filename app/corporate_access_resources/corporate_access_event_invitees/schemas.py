"""
Schemas for "corporate access event invitees" related models
"""

from marshmallow import fields, validate, validates_schema, ValidationError
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, ca_event_fields)
from app.base import constants as APP
from app.corporate_access_resources.corporate_access_event_invitees import (
    constants as CORPORATEACCESSEVENTINVITEE)
from app.corporate_access_resources.corporate_access_event_invitees.models \
    import CorporateAccessEventInvitee


# user details that will be passed while populating user relation
invitee_user_fields = user_fields + [
    'email', 'profile.phone_number', 'account.profile.profile_thumbnail_url']
user_grp_fields = ['row_id', 'crm_contact_grouped']


class CorporateAccessEventInviteeSchema(ma.ModelSchema):
    """
    Schema for loading "corporate access event invitees" from request,
    and also formatting output
    """
    invitee_email = field_for(
        CorporateAccessEventInvitee, 'invitee_email', field_class=fields.Email,
        validate=[validate.Length(
            max=CORPORATEACCESSEVENTINVITEE.INVITEE_EMAIL_MAX_LENGTH,
            error=APP.MSG_LENGTH_EXCEEDS)])

    invitee_first_name = field_for(
        CorporateAccessEventInvitee, 'invitee_first_name', validate=[
            validate.Length(
                max=CORPORATEACCESSEVENTINVITEE.INVITEE_NAME_MAX_LENGTH,
                error=APP.MSG_LENGTH_EXCEEDS)])
    invitee_last_name = field_for(
        CorporateAccessEventInvitee, 'invitee_last_name', validate=[
            validate.Length(
                max=CORPORATEACCESSEVENTINVITEE.INVITEE_NAME_MAX_LENGTH,
                error=APP.MSG_LENGTH_EXCEEDS)])
    invitee_designation = field_for(
        CorporateAccessEventInvitee, 'invitee_designation', validate=[
            validate.Length(
                max=CORPORATEACCESSEVENTINVITEE.INVITEE_DESIGNATION_MAX_LENGTH,
                error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = CorporateAccessEventInvitee
        include_fk = True
        load_only = ('updated_by', )
        dump_only = default_exclude + ('created_by', 'updated_by', 'status',
                                       'is_mail_sent', 'email_status')
        exclude = ('invitee_j',)

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor(
            'corporate_access_api.corporateaccesseventinviteeapi',
            row_id='<row_id>'),
        'collection': ma.URLFor(
            'corporate_access_api.corporateaccesseventinviteelistapi')
    }, dump_only=True)

    corporate_access_event = ma.Nested(
        'app.corporate_access_resources.'
        'corporate_access_events.schemas.CorporateAccessEventSchema',
        only=ca_event_fields, dump_only=True)
    invitee = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=invitee_user_fields,
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
        if 'invitee_id' not in data and 'invitee_email' not in data:
            error_args = [APP.MSG_NON_EMPTY, 'invitee_id, invitee_email']

        if 'invitee_id' in data and 'invitee_email' in data:
            error_args = ['Both invitee_id and invitee_email' +
                          ' should not be there', 'invitee_id, invitee_email']

        if ('invitee_id' in data and (
                'invitee_first_name' in data or
                'invitee_last_name' in data or
                'invitee_designation' in data)):
            error_args = [
                'If invitee_id is given, invitee_first_name, ' +
                'invitee_last_name and invitee_designation ' +
                'should not be there', 'invitee_id, invitee_first_name, ' +
                'invitee_last_name, invitee_designation']

        if error_args:
            raise ValidationError(*error_args)


class CAOneToOneEventInviteeSchema(ma.Schema):
    """
    Schema for one to one meeting joined or rejected event with remark
    """
    invitee_remark = fields.String(load_only=True)


class CorporateAccessEventInviteeReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "corporate access event invitees"
    filters from request args
    """
    invitee_id = fields.Integer(load_only=True)
    invitee_email = fields.Email(load_only=True)
    corporate_access_event_id = fields.Integer(load_only=True)
