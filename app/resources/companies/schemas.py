"""
Schemas for "companies" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base import constants as APP
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.resources.companies.models import Company
from app.resources.companies import constants as COMPANY
from app.resources.accounts import constants as ACCOUNT


class ManagementProfileSchema(ma.Schema):
    """
    Schema for loading "management profile" detail from request, and also
    formatting output
    """
    contact_name = fields.String()
    contact_designation = fields.String()
    contact_email = fields.Email()


class CompanySchema(ma.ModelSchema):
    """
    Schema for loading "Company" from requests, and also formatting output
    """

    company_name = field_for(Company, 'company_name', validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=COMPANY.COMPANY_NAME_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    account_type = field_for(Company, 'account_type', validate=validate.OneOf(
        ACCOUNT.ACCT_TYPES))

    management_profile = fields.List(fields.Nested(ManagementProfileSchema))

    class Meta:
        model = Company
        include_fk = True
        load_only = ('updated_by', 'created_by')
        dump_only = default_exclude + ('updated_by', 'created_by')

    links = ma.Hyperlinks({
        'self': ma.URLFor('api.companyapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.companylistapi')
    }, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    sector = ma.Nested(
        'app.resources.sectors.schemas.SectorSchema', only=['row_id', 'name'],
        dump_only=True)
    industry = ma.Nested(
        'app.resources.industries.schemas.IndustrySchema',
        only=['row_id', 'name'], dump_only=True)


class CompanyReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "Company" filters from request args
    """

    company_name = fields.String(load_only=True)
    account_type = fields.String(load_only=True, validate=validate.OneOf(
        ACCOUNT.ACCT_TYPES))
    sector_id = fields.Integer(load_only=True)
    industry_id = fields.Integer(load_only=True)
