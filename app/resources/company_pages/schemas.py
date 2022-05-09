"""
Schemas for "company pages" related models
"""

from marshmallow import fields

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, account_fields)
from app.resources.company_pages.models import CompanyPage


class CompanyAssetsSchema(ma.Schema):
    """
    Schema for company assests
    """
    type = fields.String()
    src = fields.String()
    unitDim = fields.String()
    height = fields.Integer()
    width = fields.Integer()


class CompanyPageSchema(ma.ModelSchema):
    """
    Schema for loading "company page" from requests, and also formatting output
    """
    assets = ma.List(ma.Nested(CompanyAssetsSchema))

    class Meta:
        model = CompanyPage
        include_fk = True
        load_only = ('updated_by', 'created_by', 'account_id')
        dump_only = default_exclude + ('updated_by', 'created_by',
                                       'account_id')

    links = ma.Hyperlinks({
        'self': ma.URLFor('api.companypageapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.companypagelistapi')
    }, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True)


class CompanyPageReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "company page" filters from request args
    """

    account_id = fields.Integer(load_only=True)
