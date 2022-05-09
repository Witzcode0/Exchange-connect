"""
Schemas for "corporate announcement" related models
"""

from flask import request
from marshmallow import (
    fields, pre_dump, validates_schema, ValidationError)
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, account_fields)
from app.resources.accounts import constants as ACCT
from app.resources.accounts.models import Account
from app.semidocument_resources.research_report_parameters.models import (
    ResearchReportParameter)

# files details that will be passed while populating user relation
corporate_user_fields = user_fields + [
    'account.profile.profile_photo_url',
    'account.profile.profile_thumbnail_url', 'account.identifier']
corporate_account_fields = account_fields + [
    'profile.profile_photo_url', 'profile.profile_thumbnail_url',
    'identifier']


class ResearchReportParameterSchema(ma.ModelSchema):
    """
    Schema for loading "ResearchReportParameter" from request, and also
    formatting output
    """

    class Meta:
        model = ResearchReportParameter
        include_fk = True
        load_only = ('deleted', 'updated_by', 'created_by')
        dump_only = default_exclude + (
            'updated_by', 'deleted', 'created_by')

    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema',
        only=corporate_account_fields,
        dump_only=True)


class ResearchReportParameterReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "ResearchReportParameter" filters from request args
    """
    # standard db fields
    parameter_name = fields.String(load_only=True)
    description = fields.String(load_only=True)
    account_id = fields.String(load_only=True)
    research_report_id = fields.Integer(load_only=True)

