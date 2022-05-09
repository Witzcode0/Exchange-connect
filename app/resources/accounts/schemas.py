"""
Schemas for "account" related models
"""

from marshmallow import (
    fields, validate, pre_dump, post_dump, validates_schema, ValidationError)
from marshmallow_sqlalchemy import field_for
from sqlalchemy import and_
from sqlalchemy.orm import load_only

from app import ma
from app.base import constants as APP
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.accounts.models import Account, AccountPeerGroup
from app.resources.accounts import constants as ACCOUNT


child_account_fields = ['row_id', 'account_name', 'account_type',
                        'isin_number', 'sedol', 'profile.sector.name',
                        'profile.profile_thumbnail_url', 'profile.region',
                        'profile.industry.name', 'profile.address_country',
                        'profile.address_city', 'profile.market_cap']
domain_fields = ['row_id', 'name', 'country', 'code', 'currency']


class AccountSchema(ma.ModelSchema):
    """
    Schema for loading "account" from request, and also formatting output
    """

    # default fields to exclude from the schema for speed up
    _default_exclude_fields = [
        'company_page', 'event_bookmarks', 'eventfiles', 'files', 'followers',
        'news_archive', 'notifications', 'post_comments', 'postfiles',
        'post_stars', 'posts', 'user_profiles', 'users', 'survey',
        'project_files', 'project_parameters', 'projects', 'webcasts',
        'webinars', 'newswire_posts', 'newswire_postfiles',
        'corporate_access_event_slots', 'corporate_access_events',
        'corporate_access_ref_event_sub_types', 'ca_open_meetings',
        'corporate_access_ref_event_types', 'companypagefiles',
        'ca_open_meeting_slots', 'crmlibraryfiles', 'announcements',
        'peer_accounts_j', 'research_reports_created', 'corporateaccessevents']

    account_type = field_for(Account, 'account_type', validate=validate.OneOf(
        ACCOUNT.ACCT_TYPES))
    account_name = field_for(Account, 'account_name', validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=ACCOUNT.NAME_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    stats = ma.Nested(
        'app.resources.account_stats.schemas.AccountStatsSchema',
        exclude=('account_id', 'account'), only=['total_users'],
        dump_only=True)
    profile = ma.Nested(
        'app.resources.account_profiles.schemas.AccountProfileSchema',
        exclude=['account_id', 'child_accounts', 'account'], required=True)
    settings = ma.Nested(
        'app.resources.account_settings.schemas.AccountSettingsSchema',
        exclude=['account_id', 'account'], dump_only=True)

    child_account_ids = fields.List(fields.Integer(), dump_only=True)
    _child_accounts = None
    # for validate child account exists in other group account or not
    _check_account_id = None
    _check_account_type = None

    peer_account_ids = fields.List(fields.Integer(), dump_only=True)
    _cached_peer_ids = None

    class Meta:
        model = Account
        include_fk = True
        load_only = ('deleted', 'updated_by', 'created_by', )
        dump_only = default_exclude + ('deleted', 'updated_by', 'created_by',
                                       'is_parent')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.accountapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.accountlist')
    }, dump_only=True)

    is_account_active = fields.Boolean(dump_only=True)

    account_manager = ma.Nested(
        'app.resources.account_managers.schemas.AccountManagerSchema',
        exclude=['account_id'])

    child_accounts = ma.List(ma.Nested(
        'app.resources.accounts.schemas.AccountSchema',
        only=child_account_fields, dump_only=True))

    domain = ma.Nested(
        'app.domain_resources.domains.schemas.DomainSchema',
        only=domain_fields)

    peer_groups = ma.List(ma.Nested(
        'app.resources.accounts.schemas.AccountPeerSchema', only=['peer_account'],
        ), dump_only=True)

    @pre_dump(pass_many=True)
    def load_is_account_active(self, objs, many):
        """
        Loads the active status of account
        """
        if many:
            for obj in objs:
                obj.load_is_account_active()
        else:
            objs.load_is_account_active()

    @post_dump(pass_many=True)
    def load_child_account_ids(self, objs, many):
        """
        Load child account ids
        """
        if not many:
            objs['child_account_ids'] = []
            if 'child_accounts' in objs and objs['child_accounts']:
                for ch_account in objs['child_accounts']:
                    objs['child_account_ids'].append(ch_account['row_id'])

    @validates_schema(pass_original=True)
    def validate_child_account_exists(self, data, original_data):
        """
        Validate child account exits or not and child account exists for
        another group account
        """
        error = False
        child_ids = []
        child_error = False
        cha_ids = []
        missing = []
        self._child_accounts = []
        if (((self._check_account_type and
                self._check_account_type == ACCOUNT.ACCT_CORP_GROUP) or (
                'account_type' in original_data and
                original_data['account_type'] == ACCOUNT.ACCT_CORP_GROUP)) and
                'child_account_ids' in original_data):
            cha_ids = original_data['child_account_ids'][:]
        if cha_ids:
            # make query
            caids = []
            for ch in cha_ids:
                try:
                    caids.append(int(ch))
                except Exception as e:
                    continue
            self._child_accounts = [a for a in Account.query.filter(
                and_(Account.row_id.in_(caids),
                     Account.account_type == ACCOUNT.ACCT_CORPORATE)).all()
                if not a.deleted]
            for child in self._child_accounts:
                # for post call
                if (child.activation_date and
                        child.parent_account_id and
                        not self._check_account_id):
                    child_error = True
                # for put call
                elif (child.activation_date and
                        child.parent_account_id and
                        self._check_account_id != child.parent_account_id):
                    child_error = True

                if child_error:
                    raise ValidationError(
                        'child account: ' + str(child.row_id) +
                        ' is child of another group account',
                        'child_account_ids')
                child_ids.append(child.row_id)
            missing = set(caids) - set(child_ids)
            if missing:
                error = True
        if error:
            raise ValidationError(
                'Account: %s do not exist' % missing,
                'child_account_ids')

    @validates_schema(pass_original=True)
    def validate_company_ids(self, data, original_data):
        """
        Validate that the company_ids "company" exist
        """
        error = False
        missing = []
        self._cached_peer_ids = []
        # load all the company ids
        c_ids = []
        if 'peer_account_ids' in original_data and original_data['peer_account_ids']:
            c_ids = original_data['peer_account_ids'][:]
        # validate company_ids, and load all the _cached_ids
        if c_ids:
            # make query

            cids = []
            for c in c_ids:
                try:
                    cids.append(int(c))
                except Exception as e:
                    continue
            self._cached_peer_ids = [c.row_id for c in Account.query.filter(
                and_(
                    Account.account_type == ACCOUNT.ACCT_CORPORATE,
                    Account.row_id.in_(cids))).options(load_only(
                    'row_id')).all()]
            # company_ids = [c.row_id for c in self._cached_peer_ids]
            missing = set(cids) - set(self._cached_peer_ids)
            if missing:
                error = True

        if error:
            raise ValidationError(
                'Account: %s do not exist' % missing,
                'peer_account_ids'
            )


class AccountPutSchema(AccountSchema):
    """
    Schema for extending account schema for using account_id as dump_only
    in account put functionality
    """
    profile = ma.Nested(
        'app.resources.account_profiles.schemas.AccountProfileSchema',
        exclude=['account_id'], dump_only=True, required=True)

class AccountPeerSchema(ma.ModelSchema):

    class Meta:
        model = AccountPeerGroup
        include_fk = True
        load_only = ('updated_by', 'created_by', )
        dump_only = default_exclude + ('updated_by', 'created_by', )

    peer_account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=child_account_fields,
        dump_only=True)

class AccountReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "account" filters from request args
    """
    # standard db fields
    account_name = fields.String(load_only=True)
    account_type = fields.String(load_only=True, validate=validate.OneOf(
        ACCOUNT.ACCT_TYPES))
    sector_id = fields.Integer(load_only=True)
    industry_id = fields.Integer(load_only=True)
    is_account_active = fields.Boolean(load_only=True)
    # modified date fields
    subscription_start_date_from = fields.DateTime(load_only=True)
    subscription_start_date_to = fields.DateTime(load_only=True)
    subscription_end_date_from = fields.DateTime(load_only=True)
    subscription_end_date_to = fields.DateTime(load_only=True)
    parent_account_id = fields.Integer(load_only=True)
    is_sme = fields.Boolean(load_only=True)
    blocked = fields.Boolean(load_only=True)
