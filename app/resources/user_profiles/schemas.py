"""
Schemas for "user profile" related models
"""

from marshmallow import (
    fields, pre_dump, pre_load, validate, validates_schema, ValidationError)
from marshmallow_sqlalchemy import field_for
from sqlalchemy.orm import load_only

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.base import constants as APP
from app.resources.user_profiles.models import UserProfile
from app.resources.user_profiles import constants as USER_PROFILE
from app.resources.accounts import constants as ACCOUNT
from app.resources.sectors.models import Sector
from app.resources.industries.models import Industry


# user details that will be passed while populating user relation
user_fields = ['row_id', 'links', 'email']
# account details that will be passed while populating account relation
account_fields = ['row_id', 'account_name', 'account_type']


class ExperienceSchema(ma.Schema):
    """
    Schema for loading "experience" details from request, and also
    formatting output
    """
    designation = fields.String(validate=[validate.Length(
        max=USER_PROFILE.DESIGNATION_MAX_LENGTH,
        error=APP.MSG_LENGTH_EXCEEDS)])
    company = fields.String(validate=[validate.Length(
        max=USER_PROFILE.NAME_MAX_LENGTH,
        error=APP.MSG_LENGTH_EXCEEDS)])
    company_logo = fields.String()
    location = fields.String()
    start_date = fields.DateTime()
    end_date = fields.DateTime()
    currently_working = fields.Boolean(default=False)


class EducationSchema(ma.Schema):
    """
    Schema for loading "education" details from request, and also
    formatting output
    """
    degree_name = fields.String(validate=[validate.Length(
        max=USER_PROFILE.DEGREE_NAME_MAX_LENGTH,
        error=APP.MSG_LENGTH_EXCEEDS)])
    university = fields.String(validate=[validate.Length(
        max=USER_PROFILE.NAME_MAX_LENGTH,
        error=APP.MSG_LENGTH_EXCEEDS)])
    university_logo = fields.String()
    location = fields.String()
    start_date = fields.DateTime()
    end_date = fields.DateTime()


class UserProfileSchema(ma.ModelSchema):
    """
    Schema for loading "user profile" from request, and also formatting output
    """
    experience = fields.List(fields.Nested(ExperienceSchema))
    education = fields.List(fields.Nested(EducationSchema))
    skills = fields.List(fields.String())
    interests = fields.List(fields.String())
    sector_ids = fields.List(fields.Integer())
    industry_ids = fields.List(fields.Integer())
    first_name = field_for(
        UserProfile, 'first_name', validate=[validate.Length(
            min=1, error=APP.MSG_NON_EMPTY), validate.Length(
            max=USER_PROFILE.NAME_MAX_LENGTH, error=APP.MSG_LENGTH_EXCEEDS)])
    last_name = field_for(
        UserProfile, 'last_name', validate=[validate.Length(
            min=1, error=APP.MSG_NON_EMPTY), validate.Length(
            max=USER_PROFILE.NAME_MAX_LENGTH, error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = UserProfile
        include_fk = True
        load_only = ('deleted',)
        dump_only = default_exclude + ('deleted',)
        exclude = ('account_type', 'account_id', 'company')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.userprofileapi', user_id='<user_id>'),
        'collection': ma.URLFor('api.userprofilelistapi')
    }, dump_only=True)
    cover_photo_url = ma.Url(dump_only=True)
    profile_photo_url = ma.Url(dump_only=True)
    profile_thumbnail_url = ma.Url(dump_only=True)
    cover_thumbnail_url = ma.Url(dump_only=True)
    designation_link = ma.Nested(
        'app.resources.designations.schemas.DesignationSchema', only=[
            'row_id', 'name', 'designation_level', 'sequence'], dump_only=True)

    user = ma.Nested(
        'app.resources.users.schemas.UserSchema',
        only=['settings.timezone', 'settings.search_privacy',
              'settings.allow_admin_access'], dump_only=True)
    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True)
    # special connected status as object value to indicate if current_user
    # has already connected this user
    connected = ma.Nested(
        'app.resources.contacts.schemas.ContactSchema', only=[
            'row_id', 'links'], dump_only=True)
    # special contact_requested status as object value to indicate if
    # current_user has already "contact_requested" (either send or receive)
    # this user
    contact_requested = ma.Nested(
        'app.resources.contact_requests.schemas.ContactRequestSchema', only=[
            'row_id', 'status', 'links', 'sent_by'], dump_only=True)

    @pre_dump(pass_many=True)
    def loads_urls(self, objs, many):
        """
        Loads the urls of profile photo, cover photo,
        profile thumbnail and cover thumbnail
        """
        call_load = False  # minor optimisation
        thumbnail_only = False  # default thumbnail
        if any(phfield in self.fields.keys() for phfield in [
                'profile_photo_url', 'profile_photo',
                'cover_photo_url', 'cover_photo',
                'profile_thumbnail_url', 'profile_thumbnail',
                'cover_thumbnail_url', 'cover_thumbnail']):
            # call load urls only if the above fields are asked for
            call_load = True
            if all(phfield not in self.fields.keys() for phfield in [
                    'profile_photo_url', 'profile_photo',
                    'cover_photo_url', 'cover_photo']):
                thumbnail_only = True

        if many:  # #TODO: write optimized load_url here instead?
            for obj in objs:
                if call_load:
                    obj.load_urls(thumbnail_only=thumbnail_only)
        else:
            if call_load:
                objs.load_urls(thumbnail_only=thumbnail_only)

    @validates_schema(pass_original=True)
    def validate_sector_industry_ids(self, data, original_data):
        """
        Validate that the sector_ids and industry_ids exist or not.
        """
        error_s = False  # flag for sector_ids error
        error_i = False  # flag for industry_ids error
        missing_s = []  # list for invalid sector_ids
        missing_i = []  # list for invalid industry_ids
        self._cached_sectors = []  # for sector_ids valid sector
        self._cached_industries = []  # for industry_ids valid industry

        # load all the sector ids
        s_ids = []
        if 'sector_ids' in original_data and original_data['sector_ids']:
            s_ids = original_data['sector_ids'][:]
        # validate sector_ids, and load all the _cached_sectors
        if s_ids:
            # make query
            sids = []
            for s in s_ids:
                try:
                    sids.append(int(s))
                except Exception as e:
                    continue
            self._cached_sectors = [f for f in Sector.query.filter(
                Sector.row_id.in_(sids)).options(load_only(
                    'row_id')).all()]
            sector_ids = [f.row_id for f in self._cached_sectors]
            missing_s = set(sids) - set(sector_ids)
            if missing_s:
                error_s = True

        # load all the industry ids
        i_ids = []
        if 'industry_ids' in original_data and original_data['industry_ids']:
            i_ids = original_data['industry_ids'][:]
        # validate industry_ids, and load all the _cached_industries
        if i_ids:
            # make query
            iids = []
            for i in i_ids:
                try:
                    iids.append(int(i))
                except Exception as e:
                    continue
            self._cached_industries = [f for f in Industry.query.filter(
                Industry.row_id.in_(iids)).options(load_only(
                    'row_id')).all()]
            industry_ids = [f.row_id for f in self._cached_industries]
            missing_i = set(iids) - set(industry_ids)
            if missing_i:
                error_i = True

        if error_s:
            raise ValidationError(
                'Sectors: %s do not exist' % missing_s, 'sector_ids')
        if error_i:
            raise ValidationError(
                'Industries: %s do not exist' % missing_i, 'industry_ids')

    @pre_load
    def remove_empty_skills(self, data):
        if 'skills' in data and '' in data['skills']:
            data['skills'] = []


class UserProfileAdminSchema(UserProfileSchema):
    """
    Schema for user profiles when viewed by admin users
    """
    user = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)


class UserProfileSingleGetSchema(UserProfileSchema):
    """
    Schema for single get user profile
    """
    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema',
        only=account_fields + ['profile.cover_photo_url'],
        dump_only=True)


class UserProfileReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "user profile" filters from request args
    """
    first_name = fields.String(load_only=True)
    last_name = fields.String(load_only=True)
    full_name = fields.String(load_only=True)
    company = fields.String(load_only=True)
    designation = fields.String(load_only=True)
    account_type = fields.String(load_only=True, validate=validate.OneOf(
        ACCOUNT.ACCT_TYPES))
    account_id = fields.Integer(load_only=True)
    sector_id = fields.Integer(load_only=True)
    industry_id = fields.Integer(load_only=True)
    not_of_account_type = fields.String(
        load_only=True, validate=validate.OneOf(ACCOUNT.ACCT_TYPES))


class UserProfileChatSchema(UserProfileSchema):
    """
    Schema for loading required user profile details for the chat.
    """
    class Meta:
        fields = ['first_name', 'last_name', 'user_id', 'profile_photo_url',
                  'profile_thumbnail_url']


class UserProfileChatReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "user profile chat" filters from request args
    """
    user_ids = fields.List(fields.Integer(), load_only=True)
