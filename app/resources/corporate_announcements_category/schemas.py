"""
Schemas for "corporate announcement category_keywords" related models
"""
from marshmallow import (
    fields, validate, pre_dump, pre_load, validates_schema, ValidationError)
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, account_fields)
from app.resources.corporate_announcements_category.models import \
    CorporateAnnouncementCategory

# files details that will be passed while populating user relation
corporate_user_fields = user_fields + [
    'account.profile.profile_photo_url',
    'account.profile.profile_thumbnail_url', 'account.identifier']
corporate_account_fields = account_fields + [
    'profile.profile_photo_url', 'profile.profile_thumbnail_url',
    'identifier']

class CorporateAnnouncementCategorySchema(ma.ModelSchema):
    """
    Schema for loading "CorporateAnnouncement" from request, and also
    formatting output
    """

    class Meta:
        model = CorporateAnnouncementCategory
        include_fk = True
        load_only = ('deleted', 'updated_by', 'created_by')
        dump_only = default_exclude + (
            'updated_by', 'deleted', 'created_by')

    # creator = ma.Nested(
    #     'app.resources.users.schemas.UserSchema', only=corporate_user_fields,
    #     dump_only=True)
    # editor = ma.Nested(
    #     'app.resources.users.schemas.UserSchema', only=corporate_user_fields,
    #     dump_only=True)


class AdminCorporateAnnouncementCategorySchema(CorporateAnnouncementCategorySchema):
    """
    Schema for loading "CorporateAnnouncementCategory" from request for Admin, and also
    formatting output
    """

    class Meta:
        model = CorporateAnnouncementCategory
        include_fk = True
        load_only = ('deleted', 'updated_by', 'created_by')
        dump_only = default_exclude + ('updated_by', 'deleted', 'created_by')


class CorporateAnnouncementCategoriesSchema(ma.ModelSchema):
    """
    Schema for loading "CorporateAnnouncement" from request, and also
    formatting output
    """

    class Meta:
        model = CorporateAnnouncementCategory
        include_fk = False
        load_only = ('deleted', 'updated_by', 'created_by', 'category_id', 'cat_id', 'ec_category')
        dump_only = default_exclude + (
            'updated_by', 'deleted', 'created_by')


class CorporateAnnouncementCategoryReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "CorporateAnnouncement" filters from request args
    """
    # standard db fields
    name = fields.String(load_only=True)
    subject_keywords = fields.String(load_only=True)
    category_keywords = fields.String(load_only=True)