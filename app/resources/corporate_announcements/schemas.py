"""
Schemas for "corporate announcement" related models
"""

from flask import request
from marshmallow import (
    fields, validate, pre_dump, pre_load, validates_schema, ValidationError)
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, account_fields)
from app.resources.corporate_announcements import constants as \
    CORP_ANNOUNCEMENT
from app.resources.corporate_announcements.models import \
    CorporateAnnouncement


# files details that will be passed while populating user relation
corporate_user_fields = user_fields + [
    'account.profile.profile_photo_url',
    'account.profile.profile_thumbnail_url', 'account.identifier']
corporate_account_fields = account_fields + [
    'profile.profile_photo_url', 'profile.profile_thumbnail_url',
    'identifier']


class CorporateAnnouncementSchema(ma.ModelSchema):
    """
    Schema for loading "CorporateAnnouncement" from request, and also
    formatting output
    """

    # default fields to exclude from the schema for speed up
    _default_exclude_fields = ['posts']
    _open_api_db_proj = ['row_id', 'subject', 'category', 'file',
                         'url', 'announcement_date']
    _open_api_s_proj = _open_api_db_proj + [
        'account.account_name', 'account.row_id']

    category = field_for(
        CorporateAnnouncement, 'category', validate=validate.OneOf(
            CORP_ANNOUNCEMENT.CANNC_CATEGORY_TYPES))

    class Meta:
        model = CorporateAnnouncement
        include_fk = True
        load_only = ('deleted', 'account_id', 'updated_by', 'created_by')
        dump_only = default_exclude + (
            'account_id', 'updated_by', 'deleted', 'created_by',
            'ca_event_audio_file_id', 'ca_event_transcript_file_id')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.corporateannouncementapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.corporateannouncementlistapi')
    }, dump_only=True)

    file_url = ma.Url(dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=corporate_user_fields,
        dump_only=True)
    editor = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=corporate_user_fields,
        dump_only=True)
    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema',
        only=corporate_account_fields,
        dump_only=True)
    ca_event_transcript_file = ma.Nested(
        'app.corporate_access_resources.'
        'corporate_access_events.schemas.CorporateAccessEventSchema',
        only=['transcript_filename', 'transcript_url'], dump_only=True)
    ca_event_audio_file = ma.Nested(
        'app.corporate_access_resources.'
        'corporate_access_events.schemas.CorporateAccessEventSchema',
        only=['audio_filename', 'audio_url'], dump_only=True)
    ec_category = ma.Nested(
        'app.resources.corporate_announcements_category.schemas.CorporateAnnouncementCategorySchema',
        only=['name', 'row_id'],dump_only=True)

    @pre_dump(pass_many=True)
    def loads_urls(self, objs, many):
        """
        Loads the url of file
        """
        call_load = False  # minor optimisation
        if any(phfield in self.fields.keys() for phfield in [
                'file_url', 'file']):
            # call load urls only if the above fields are asked for
            call_load = True

        if many:  # #TODO: write optimized load_url here instead?
            for obj in objs:
                if call_load:
                    obj.load_urls()
        else:
            if call_load:
                objs.load_urls()

    @validates_schema
    def validate_file_and_url(self, data):
        """
        Validate that file and url both should not be there in data
        """
        error = False
        if ('file' in request.files and 'url' in data and data['url']):
            # <- file is present in data
            # <- url is present in data
            error = True
        if 'file' in data and data['file'] and 'url' in data and data['url']:
            error = True

        if error:
            raise ValidationError('Both are there in data', 'file and url')


class AdminCorporateAnnouncementSchema(CorporateAnnouncementSchema):
    """
    Schema for loading "CorporateAnnouncement" from request for Admin, and also
    formatting output
    """

    class Meta:
        model = CorporateAnnouncement
        include_fk = False
        load_only = ('deleted', 'updated_by', 'created_by')
        dump_only = default_exclude + ('updated_by', 'deleted', 'created_by')


class CorporateAnnouncementReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "CorporateAnnouncement" filters from request args
    """
    # standard db fields
    category = fields.String(load_only=True, validate=validate.OneOf(
        CORP_ANNOUNCEMENT.CANNC_CATEGORY_TYPES))
    subject = fields.String(load_only=True)
    description = fields.String(load_only=True)
    company_id = fields.String(load_only=True)
    company_name = fields.String(load_only=True)
    following = fields.Boolean(load_only=True)
    categories = fields.List(fields.String(), load_only=True)
    category_id = fields.Integer(load_only=True)


class GlobalAnnouncementSchema(ma.Schema):
    """
    Schema for global activity
    """
    # Announcement
    row_id = fields.Integer(dump_only=True)
    created_date = fields.DateTime(dump_only=True)
    modified_date = fields.DateTime(dump_only=True)
    source = fields.String(dump_only=True)
    announcement_date = fields.DateTime(dump_only=True)
    subject = fields.String(dump_only=True)
    description = fields.String(dump_only=True)
    file = fields.String(dump_only=True)
    url = fields.String(dump_only=True)
    file_url = fields.String(dump_only=True)
    bse_descriptor = fields.String(dump_only=True)
    type_of_announce = fields.String(dump_only=True)
    ca_event_audio_file_id = fields.Integer(dump_only=True)
    ca_event_transcript_file_id = fields.Integer(dump_only=True)
    # Account
    account_name = fields.String(dump_only=True)
    account_identifier = fields.String(dump_only=True)
    account_row_id = fields.Integer(dump_only=True)
    account_type = fields.String(dump_only=True)
    # Creator
    creator_name = fields.String(dump_only=True)
    modifier_name = fields.String(dump_only=True)
    # Category
    category = fields.String(dump_only=True)
    ec_category_name = fields.String(dump_only=True)
    ec_category_row_id = fields.Integer(dump_only=True)


class GlobalAnnouncementReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "global activity" filters from request args
    """
    # Todo :- default sort to modified_date
    company_id = fields.Integer(load_only=True)
    # category = fields.String(load_only=True, validate=validate.OneOf(
    #     CORP_ANNOUNCEMENT.CANNC_CATEGORY_TYPES))
    subject = fields.String(load_only=True)
    # description = fields.String(load_only=True)
    # company_name = fields.String(load_only=True)
    following = fields.Boolean(load_only=True)
    # categories = fields.List(fields.String(), load_only=True)
    category_id = fields.Integer(load_only=True)
