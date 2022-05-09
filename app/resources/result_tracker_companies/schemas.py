"""
Schemas for "result tracker group" related schema
"""
from marshmallow import fields
from app import ma
from app.resources.result_tracker_companies.models import ResultTrackerGroupCompanies
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.base.schemas import account_fields
from app.resources.results.schemas import AccountResultTrackerSchema

corporate_account_fields = account_fields + [
    'profile.profile_photo_url', 'profile.profile_thumbnail_url',
    'identifier']


class ResultTrackerGroupCompaniesSchema(ma.ModelSchema):
    """
    Schema for loading data from bse api
    """
    class Meta:
        model = ResultTrackerGroupCompanies
        include_fk = True
        load_only = ('updated_by', 'created_by')
        dump_only = default_exclude + ('updated_by', 'created_by')

    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema',
        only=corporate_account_fields,
        dump_only=True)

    group = ma.Nested('app.resources.result_tracker.schemas.ResultTrackerGroupSchema',
                      only=['row_id', 'group_name'],
                      dump_only=True)


class ResultTrackerGroupCompaniesArgsSchema(BaseReadArgsSchema):
    """
        Schema for reading "result tracker group companies" filters from request args
    """
    sort_by = fields.List(fields.String(), load_only=True, missing=[
        'sequence_id'])
