"""
Schemas for "registration requests" related models
"""

import base64

from marshmallow import fields, validate, pre_load
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base import constants as APP
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.registration_requests import constants as REGREQUEST
from app.resources.registration_requests.models import RegistrationRequest
from app.resources.accounts import constants as ACCOUNT
from app.resources.users import constants as USER

domain_fields = ['row_id', 'name', 'country', 'code', 'currency']

class RegistrationRequestSchema(ma.ModelSchema):
    """
    Schema for loading "RegistrationRequest" from request, and also
    formatting output
    """

    email = field_for(RegistrationRequest, 'email', field_class=fields.Email)
    password = field_for(
        RegistrationRequest, 'password', validate=validate.Regexp(
            APP.STRONG_PASSWORD))
    join_as = field_for(
        RegistrationRequest, 'join_as', validate=validate.OneOf(
            ACCOUNT.ACCT_TYPES))
    status = field_for(RegistrationRequest, 'status', validate=validate.OneOf(
        REGREQUEST.REQ_STATUS_TYPES))
    first_name = field_for(RegistrationRequest, 'first_name',
                           validate=[validate.Length
                                     (min=1, error=APP.MSG_NON_EMPTY),
                                     validate.Length
                                     (max=REGREQUEST.NAME_MAX_LENGTH,
                                      error=APP.MSG_LENGTH_EXCEEDS)])
    last_name = field_for(RegistrationRequest, 'last_name',
                          validate=[validate.Length
                                    (min=1, error=APP.MSG_NON_EMPTY),
                                    validate.Length
                                    (max=REGREQUEST.NAME_MAX_LENGTH,
                                     error=APP.MSG_LENGTH_EXCEEDS)])
    domain = ma.Nested('app.domain_resources.domains.schemas.DomainSchema',
                       only=domain_fields)

    class Meta:
        model = RegistrationRequest
        include_fk = True
        load_only = ('deleted', 'updated_by', 'password')
        dump_only = default_exclude + ('updated_by', 'deleted', 'domain_id',
                                       'welcome_mail_sent')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.registrationrequestapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.registrationrequestlist')
    })

    @pre_load(pass_many=True)
    def convert_email_and_password(self, objs, many):
        """
        Covert email and password from base64 to string
        :return:
        """
        if 'password' in objs and objs['password']:
            objs['password'] = base64.b64decode(
                objs['password']).decode('utf-8')


class RegistrationRequestReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "RegistrationRequest" filters from request args
    """

    # standard db fields
    full_name = fields.String(load_only=True)
    email = fields.String(load_only=True)
    first_name = fields.String(load_only=True)
    last_name = fields.String(load_only=True)
    company = fields.String(load_only=True)
    designation = fields.String(load_only=True)
    phone_number = fields.String(load_only=True)
    status = fields.List(fields.String(validate=validate.OneOf(
        REGREQUEST.REQ_STATUS_TYPES), load_only=True))
    updated_by = fields.Integer(load_only=True)
    by_admin = fields.Boolean(load_only=True)
    join_as = fields.String(load_only=True, validate=validate.OneOf(
        ACCOUNT.ACCT_TYPES))


class UserProfileCommonSchema(ma.Schema):
    """
    Schema for user and user profile common info, and validation
    from json request
    """

    email = fields.Email(required=True)
    first_name = fields.String(required=True)
    last_name = fields.String(required=True)
    company = fields.String(missing=None)
    designation = fields.String(missing=None)
    phone_number = fields.String(missing=None)
    role_id = fields.Integer(required=True)
    account_id = fields.Integer(required=True)
    is_admin = fields.Boolean()
