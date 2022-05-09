"""
Schemas for "follows" related models
"""

from marshmallow import fields, validate, validates_schema, ValidationError

from app import ma, g
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.resources.follows.models import CFollow, CFollowHistory
from app.resources.follows import constants as CFOLLOW
from app.resources.accounts import constants as ACCOUNT


# account fields
account_fields = ['account_name', 'account_type']
# add designation link to user_fields
user_fields += ['account.account_type', 'profile.designation_link']


class CFollowSchema(ma.ModelSchema):
    """
    Schema for formatting contacts
    """

    class Meta:
        model = CFollow
        include_fk = True
        dump_only = default_exclude + ('sent_by', )
        exclude = ('company_j', )

    links = ma.Hyperlinks({
        'self': ma.URLFor('api.cfollowapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.cfollowlistapi')
    }, dump_only=True)

    follower = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    company = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=(
            'row_id', 'account_type', 'account_name',
            'profile.profile_photo_url', 'profile.profile_thumbnail_url',
            'profile.country', 'profile.sector',
            'profile.industry'), dump_only=True)

    @validates_schema(pass_original=True)
    def validate_not_self_follow(self, data, original_data):
        """
        Validate that user can not follow her own company!
        """
        if ('company_id' in data and
                data['company_id'] == g.current_user['account_id']):
            raise ValidationError(
                'Can not follow own company', 'company_id')


class CFollowHistorySchema(ma.ModelSchema):
    """
    Schema for contact history
    """
    class Meta:
        model = CFollowHistory


class CFollowReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for read args
    """
    following_follower = fields.String(
        load_only=True, missing=CFOLLOW.CF_FOLLOWING,
        validate=validate.OneOf(CFOLLOW.CF_FOLLOWING_FOLLOWER_TYPES))
    account_name = fields.String(load_only=True)
    account_type = fields.String(load_only=True, validate=validate.OneOf(
        ACCOUNT.ACCT_TYPES))
    sector_id = fields.Integer(load_only=True)
    industry_id = fields.Integer(load_only=True)


class CFollowAnalysisSchema(ma.Schema):
    """
    Schema for company follow analysis
    """
    total_follow_by_designation = fields.Integer(dump_only=True)
    designation_level = fields.String(dump_only=True)
