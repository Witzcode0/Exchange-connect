"""
Schemas for "account profile" related models
"""

from marshmallow import fields, validate, pre_dump
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.account_profiles import constants as ACCT_PROFILE
from app.resources.account_profiles.models import AccountProfile
from app.resources.accounts import constants as ACCOUNT


# account details that will be passed while populating account relation
account_fields = ['account_name', 'account_type', 'is_account_active',
                  'isin_number', 'account_manager.manager.email',
                  'account_manager.manager.profile', 'is_sme']
child_account_fields = ['row_id', 'account_name', 'account_type',
                        'isin_number', 'sedol', 'profile.sector.name',
                        'profile.profile_thumbnail_url', 'profile.region',
                        'profile.industry.name', 'profile.address_country',
                        'profile.address_city', 'profile.market_cap']


class AccountProfileSchema(ma.ModelSchema):
    """
    Schema for loading "AccountProfile" from request, and also
    formatting output
    """

    cap_group = field_for(AccountProfile, 'cap_group', validate=validate.OneOf(
        ACCT_PROFILE.CAP_TYPES))
    top_ten_holdings_percentage = field_for(
        AccountProfile, 'top_ten_holdings_percentage', as_string=True)
    management_profiles = ma.List(ma.Nested(
        'app.resources.management_profiles.schemas.ManagementProfileSchema',
        exclude=['account_profile_id']))

    class Meta:
        model = AccountProfile
        include_fk = True
        load_only = ('deleted', 'updated_by', 'created_by')
        dump_only = default_exclude + ('updated_by', 'deleted', 'created_by')
        exclude = ('account_type', )

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.accountprofileapi', account_id='<account_id>'),
        'collection': ma.URLFor('api.accountprofilelistapi')
    }, dump_only=True)

    cover_photo_url = ma.Url(dump_only=True)
    profile_photo_url = ma.Url(dump_only=True)
    profile_thumbnail_url = ma.Url(dump_only=True)
    cover_thumbnail_url = ma.Url(dump_only=True)

    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True)

    child_accounts = ma.List(ma.Nested(
        'app.resources.accounts.schemas.AccountSchema',
        only=child_account_fields, dump_only=True))
    # special followed status as object value to indicate if current_user
    # has already followed this account (company)
    followed = ma.Nested(
        'app.resources.follows.schemas.CFollowSchema', only=[
            'row_id', 'links'], dump_only=True)
    sector = ma.Nested(
        'app.resources.sectors.schemas.SectorSchema',
        only=['row_id', 'name'], dump_only=True)
    industry = ma.Nested(
        'app.resources.industries.schemas.IndustrySchema',
        only=['row_id', 'name'], dump_only=True)

    @pre_dump(pass_many=True)
    def loads_urls(self, objs, many):
        """
        Loads the urls of profile photo, cover photo,
        profile thumbnail and cover thumbnail
        """
        call_load = False  # minor optimisation
        thumbnail_only = False  # default thumbnail
        call_mngmt = False  # management profile
        if any(phfield in self.fields.keys() for phfield in [
                'profile_photo_url', 'profile_photo',
                'cover_photo_url', 'cover_photo',
                'profile_thumbnail_url', 'profile_thumbnail',
                'cover_thumbnail_url', 'cover_thumbnail',
                'management_profiles']):
            # call load urls only if the above fields are asked for
            call_load = True
            call_mngmt = True
            if all(phfield not in self.fields.keys() for phfield in [
                    'profile_photo_url', 'profile_photo',
                    'cover_photo_url', 'cover_photo']):
                thumbnail_only = True

        if many:  # #TODO: write optimized load_url here instead?
            for obj in objs:
                if call_load:
                    obj.load_urls(thumbnail_only=thumbnail_only)
                if call_mngmt:
                    obj.sort_management()
        else:
            if call_load:
                objs.load_urls(thumbnail_only=thumbnail_only)
            if call_mngmt:
                objs.sort_management()


class AccountProfileListSchema(AccountProfileSchema):
    """
    Schema for common used account profile
    """
    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=[
            'account_name', 'account_type', 'is_account_active',
            'isin_number'], dump_only=True)

    management_profiles = ma.List(ma.Nested(
        'app.resources.management_profiles.schemas.ManagementProfileSchema'),
        only=['row_id', 'account_profile_id', 'name', 'designation',
              'description', 'profile_photo_url'], dump_only=True)


class AccountProfileReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "AccountProfile" filters from request args
    """
    # standard db fields
    account_name = fields.String(load_only=True)
    account_type = fields.String(load_only=True, validate=validate.OneOf(
        ACCOUNT.ACCT_TYPES))
    sector_id = fields.Integer(load_only=True)
    industry_id = fields.Integer(load_only=True)
    region = fields.String(load_only=True)
    country = fields.String(load_only=True)
    institution_type = fields.String(load_only=True)
    institution_style = fields.String(load_only=True)
    currency = fields.String(load_only=True)
    cap_group = fields.String(load_only=True, validate=validate.OneOf(
        ACCT_PROFILE.CAP_TYPES))
    not_of_account_type = fields.String(
        load_only=True, validate=validate.OneOf(ACCOUNT.ACCT_TYPES))
    is_account_active = fields.Boolean(load_only=True)
    parent_account_id = fields.Integer(load_only=True)


class AccountProfileTeamReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "user profile" filters from request args
    """

    full_name = fields.String(load_only=True)
    account_id = fields.Integer(load_only=True, required=True)
