"""
Schemas for "user settings" related models
"""

from flask import g
from marshmallow import (
    fields, validate, validates_schema, ValidationError, pre_dump)
from marshmallow_sqlalchemy import field_for
from sqlalchemy.orm import load_only

from app import ma
from app.base.schemas import default_exclude, user_fields
from app.base import constants as APP
from app.resources.users import constants as USER
from app.resources.accounts import constants as ACCOUNT
from app.resources.designations import constants as DESIG
from app.resources.user_settings.models import UserSettings
from app.resources.sectors.models import Sector
from app.resources.industries.models import Industry


class CRMCustomizeViewSchema(ma.Schema):
    """
    Schema for CRM Dashboard customize view
    """
    name = fields.String()
    is_selected = fields.Boolean(missing=True)
    sequence_id = fields.Integer(validate=validate.Range(
            min=APP.SEQUENCE_ID_MIN_VALUE,
            error=APP.SEQUENCE_ID_MIN_VALUE_ERROR))


class UserSettingsSchema(ma.ModelSchema):
    """
    Schema for loading "user settings" from request, and also formatting output
    """
    search_privacy = fields.List(field_for(
        UserSettings, 'search_privacy',
        validate=validate.OneOf(ACCOUNT.ACCT_TYPES)))
    timezone = field_for(
        UserSettings, 'timezone', validate=validate.OneOf(USER.ALL_TIMEZONES))
    language = field_for(
        UserSettings, 'language', validate=validate.OneOf(
            USER.AVAILABLE_LANGUAGES))
    search_privacy_market_cap_min = field_for(
        UserSettings, 'search_privacy_market_cap_min', as_string=True)
    search_privacy_market_cap_max = field_for(
        UserSettings, 'search_privacy_market_cap_max', as_string=True)
    search_privacy_designation_level = fields.List(field_for(
        UserSettings, 'search_privacy_designation_level',
        validate=validate.OneOf(DESIG.DES_LEVEL_TYPES)))
    crm_customize_view = ma.List(ma.Nested(CRMCustomizeViewSchema))

    class Meta:
        model = UserSettings
        include_fk = True
        load_only = ('deleted',)
        dump_only = default_exclude + ('deleted',)

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.usersettingsapi')
    }, dump_only=True)

    user = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)

    @pre_dump(pass_many=True)
    def loads_urls(self, objs, many):
        """
        Loads the sorting crm customize view by sequence id
        """

        if not many:
            objs.sort_crm_customize_view()

    # #TODO: May be used in future
    # @validates_schema(pass_original=True)
    def validate_not_same_account_type(self, data, original_data):
        """
        Validate that user cannot add same account type in privacy settings
        """
        if 'search_privacy' in data:
            if g.current_user['account_type'] in data['search_privacy']:
                raise ValidationError(
                    'Can not add same account type %s in privacy settings' %
                    g.current_user['account_type'], 'search_privacy')

    @validates_schema(pass_original=True)
    def validate_search_privacy_sector_and_industry(self, data, original_data):
        """
        Validate that the search_privacy_sector and search_privacy_industry
        exist or not.
        """
        error_s = False  # flag for search_privacy_sector error
        error_i = False  # flag for search_privacy_industry error
        missing_s = []  # list for invalid search_privacy_sectors
        missing_i = []  # list for invalid search_privacy_industries
        self._cached_sectors = []  # for search_privacy_sector valid sector
        self._cached_industries = []  # search_privacy_industry valid industry

        # load all the search_privacy_sectors
        s_ids = []
        if 'search_privacy_sector' in original_data and original_data[
                'search_privacy_sector']:
            s_ids = original_data['search_privacy_sector'][:]
        # validate search_privacy_sector, and load all the _cached_sectors
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
            search_privacy_sector = [f.row_id for f in self._cached_sectors]
            missing_s = set(sids) - set(search_privacy_sector)
            if missing_s:
                error_s = True

        # load all the search_privacy_industries
        i_ids = []
        if 'search_privacy_industry' in original_data and original_data[
                'search_privacy_industry']:
            i_ids = original_data['search_privacy_industry'][:]
        # validate search_privacy_industry, and load all the _cached_industries
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
            search_privacy_industry = [f.row_id for f in
                                       self._cached_industries]
            missing_i = set(iids) - set(search_privacy_industry)
            if missing_i:
                error_i = True

        if error_s:
            raise ValidationError(
                'Sectors: %s do not exist' % missing_s,
                'search_privacy_sector')
        if error_i:
            raise ValidationError(
                'Industries: %s do not exist' % missing_i,
                'search_privacy_industry')
