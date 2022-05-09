"""
Schemas for "bse corporate data" related models
"""
from marshmallow import fields
from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.bse.models import BSEFeed
from app.resources.descriptor.models import BSE_Descriptor
from app.base.schemas import account_fields

corporate_account_fields = account_fields + [
    'profile.profile_photo_url', 'profile.profile_thumbnail_url',
    'identifier']


class BseCorpSchema(ma.ModelSchema):
    """
    Schema for loading data from bse api
    """
    class Meta:
        model = BSEFeed
        include_fk = True
        load_only = ('deleted', 'updated_by', 'created_by')
        dump_only = default_exclude + ('updated_by', 'created_by')

    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema',
        only=corporate_account_fields,
        dump_only=True)

    category = ma.Nested(
        'app.resources.corporate_announcements_category.schemas.CorporateAnnouncementCategorySchema',
        only=['name', 'row_id'],
        dump_only=True)


class BseDescriptorSchema(ma.ModelSchema):
    """
    Schema for loading data from BSE_Descriptor
    """
    class Meta:
        model = BSE_Descriptor
        include_fk = True


class BseFeedReadArgsSchema(BaseReadArgsSchema):
    """
        Schema for reading "bse feed item" filters from request args
    """
    company_name = fields.String(load_only=True)
    news_sub = fields.String(load_only=True)
    descriptor = fields.String(load_only=True)
    from_date = fields.DateTime(load_only=True)
    to_date = fields.DateTime(load_only=True)
    category_id = fields.Integer(load_only=True)
    following = fields.Boolean(load_only=True)


class BseFeedStatsSchema(ma.Schema):
    """
    Schema for loading counts of bse feed by category
    """
    total_annual_report = fields.Integer(dump_only=True)
    total_company_updates = fields.Integer(dump_only=True)
    total_shareholder_meeting = fields.Integer(dump_only=True)
    total_disclosure = fields.Integer(dump_only=True)
    total_board_meeting = fields.Integer(dump_only=True)
    total_result_update_and_concall_transcripts = fields.Integer(dump_only=True)
    total_analyst_investor_meet_and_presentation = fields.Integer(dump_only=True)



class BseFeedStatsReadArgsSchema(BaseReadArgsSchema):
    pass
