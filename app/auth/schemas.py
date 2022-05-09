"""
Schemas for "auth" related models
"""

import base64

from marshmallow import fields, pre_load, validate

from app import ma, jwt
from app.resources.users.models import User
from app.base import constants as APP


@jwt.user_claims_loader
def add_claims_to_access_token(identity):
    return {
        'hello': identity,
        'foo': ['bar', 'baz']
    }


class LoginSchema(ma.Schema):
    """
    Schema for reading login credentials
    """
    email = fields.Email(required=True)
    password = fields.String(required=True)
    device_request_id = fields.String(load_only=True)

    @pre_load(pass_many=True)
    def convert_email_and_password(self, objs, many):
        """
        Covert email and password from base64 to string
        :return:
        """
        if 'email' in objs and objs['email']:
            objs['email'] = base64.b64decode(objs['email']).decode('utf-8')
        if 'password' in objs and objs['password']:
            objs['password'] = base64.b64decode(
                objs['password']).decode('utf-8')

# user profile fields
user_profile_fields = ['first_name', 'last_name', 'profile_photo_url',
                       'designation_link', 'profile_thumbnail_url',
                       'phone_number']
# account details that will be passed while populating account relation
current_account_fields = ['row_id', 'account_name', 'account_type',
                          'identifier', 'isin_number', 'sedol',
                          'subscription_start_date', 'subscription_end_date',
                          'is_download_report', 'export_enabled',
                          'profile.sector', 'profile.industry']
account_fields = current_account_fields[:]
# role details that will be passed while populating role relation
role_fields = ['row_id', 'name']


class UserIdentitySchema(ma.ModelSchema):
    """
    Schema for formatting jwt user identity
    """
    from_mobile = fields.String()

    class Meta:
        model = User
        include_fk = True
        exclude = (
            'created_date', 'modified_date', 'password', 'updated_by',
            'created_by', 'deleted', 'tasks', 'role_id', 'token_valid',
            'token_valid_mobile')

    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True)
    role = ma.Nested(
        'app.resources.roles.schemas.RoleSchema', only=role_fields,
        dump_only=True)
    profile = ma.Nested(
        'app.resources.user_profiles.schemas.UserProfileSchema',
        only=user_profile_fields, dump_only=True)
    current_account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema',
        only=current_account_fields, dump_only=True)


class SwitchAccountUserSchema(ma.Schema):
    """
    Schema for switch account user
    """
    child_account_id = fields.Integer(required=True)


class ChildAccountUserSchema(ma.Schema):
    """
    Schema for switch account user
    """
    child_account_id = fields.Integer()


class EmailSchema(ma.Schema):
    """
    Schema for forgot password email
    """
    email = fields.Email(required=True)


class ResetPasswordSchema(ma.ModelSchema):
    """
    Schema for reset password
    """
    password = fields.String(required=True, validate=validate.Regexp(
        APP.STRONG_PASSWORD))

    class Meta:
        model = User
        fields = ("password", )

    @pre_load(pass_many=True)
    def convert_email_and_password(self, objs, many):
        """
        Covert email and password from base64 to string
        :return:
        """
        if 'password' in objs and objs['password']:
            objs['password'] = base64.b64decode(
                objs['password']).decode('utf-8')


class UserLoginReadArgsSchema(ma.Schema):
    """
    schema for common api while login
    """
    from_mobile = fields.Boolean()  # user login from mobile device


class TokenVerificationSchema(ma.Schema):
    """
    schema for user verification for access to ownership analysis,
    disclosure enhancement and investor targeting
    """
    user_token = fields.String(required=True)
