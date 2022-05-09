"""
Schemas for "crm contact" related models
"""

from marshmallow import (
    fields, validate, pre_dump, ValidationError, validates_schema)
from marshmallow_sqlalchemy import field_for
from sqlalchemy.orm import load_only

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.crm_resources.crm_contacts.models import CRMContact, FundManagement
from app.crm_resources.crm_file_library.models import CRMLibraryFile
from app.crm_resources.crm_contacts import constants as CRM
from app.resources.industries.models import Industry
from app.resources.accounts import constants as ACCOUNT

# user details that will be passed while populating user relation
# user profile details
user_profile_fields = ['first_name', 'last_name', 'designation',
                       'profile_thumbnail_url', 'address_street_one',
                       'address_street_two', 'address_city', 'address_state',
                       'address_zip_code', 'address_country']
user_fields = ['row_id', 'email', 'crm_contact_grouped', 'account_id']
user_fields += ['profile.' + fld for fld in user_profile_fields]


class CRMContactFactsetFundManagementSchema(ma.ModelSchema):
    """
    Schema for loading "funds" from request, and also formatting output
    """
    class Meta:
        model = FundManagement
        include_fk = True
        exclude= ('crm_contact_fund_management',)


class CRMContactSchema(ma.ModelSchema):
    """
    Schema for loading "crm contact" from request, and also formatting output
    """

    email = field_for(CRMContact, 'email', field_class=fields.Email)
    contact_type = field_for(
        CRMContact, 'contact_type', validate=validate.OneOf(
            ACCOUNT.CRM_ACCT_TYPES))
    _cached_files = None
    file_ids = fields.List(fields.Integer(), dump_only=True)

    class Meta:
        model = CRMContact
        include_fk = True
        load_only = ('created_by', 'account_id',)
        dump_only = default_exclude + ('created_by', 'account_id', 'user_id')
        exclude = ('crmcontactgrouped', 'group_j', )

    profile_photo_url = ma.Url(dump_only=True)
    profile_thumbnail_url = ma.Url(dump_only=True)

    industry_coverages = ma.List(ma.Nested(
        'app.resources.industries.schemas.IndustrySchema',
        only=['row_id', 'name']), dump_only=True)
    user = ma.Nested('app.resources.users.schemas.UserSchema',
                     only=user_fields, dump_only=True)

    fund_management = ma.List(ma.Nested(
        'app.crm_resources.crm_contacts.schemas.CRMContactFactsetFundManagementSchema',
        dump_only=True))

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
                'profile_thumbnail_url', 'profile_thumbnail']):
            # call load urls only if the above fields are asked for
            call_load = True
            if all(phfield not in self.fields.keys() for phfield in [
                    'profile_photo_url', 'profile_photo']):
                thumbnail_only = True

        if many:  # #TODO: write optimized load_url here instead?
            for obj in objs:
                if call_load:
                    obj.load_urls(thumbnail_only=thumbnail_only)
                    obj.load_industry_coverage()
        else:
            if call_load:
                objs.load_urls(thumbnail_only=thumbnail_only)
                objs.load_industry_coverage()

    @validates_schema(pass_original=True)
    def validate_industry_coverage(self, data, original_data):
        """
        Validate that the industry_coverage exist
        """
        error = False
        missing = []
        if ('industry_coverage' in original_data and
                original_data['industry_coverage']):
            # make query
            iids = [int(cid) for cid in original_data['industry_coverage']]
            industry_coverages = [c.row_id for c in Industry.query.filter(
                Industry.row_id.in_(iids)).options(load_only(
                    'row_id')).all()]
            missing = set(iids) - set(industry_coverages)
            if missing:
                error = True
            data['industry_coverage'] = industry_coverages
        if error:
            raise ValidationError(
                'Industry: %s do not exist' % missing,
                'industry_coverage')

    @validates_schema(pass_original=True)
    def validate_file_ids(self, data, original_data):
        """
        Validate that the file_ids "crm library file" exist
        """
        error = False
        missing = []
        self._cached_files = []
        # load all the file ids
        f_ids = []
        if 'file_ids' in original_data and original_data['file_ids']:
            f_ids = original_data['file_ids'][:]
        # validate file_ids, and load all the _cached_files
        if f_ids:
            # make query
            fids = []
            for f in f_ids:
                try:
                    fids.append(int(f))
                except Exception as e:
                    continue
            self._cached_files = [f for f in CRMLibraryFile.query.filter(
                CRMLibraryFile.row_id.in_(fids)).options(load_only(
                    'row_id', 'deleted')).all() if not f.deleted]
            file_ids = [f.row_id for f in self._cached_files]
            missing = set(fids) - set(file_ids)
            if missing:
                error = True

        if error:
            raise ValidationError(
                'Files: %s do not exist' % missing,
                'file_ids'
            )


class CRMContactReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "crm contact" filters from request args
    """
    email = fields.String(load_only=True)
    first_name = fields.String(load_only=True)
    last_name = fields.String(load_only=True)
    contact_type = fields.String(load_only=True, validate=validate.OneOf(
        ACCOUNT.CRM_ACCT_TYPES))
    company = fields.String(load_only=True)
    designation = fields.String(load_only=True)
    factset_person_id = fields.String(load_only=True)


class CRMCommonConnectionSchema(ma.Schema):
    """
    Schema for common connection
    """

    user = fields.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    contact_id = fields.Integer(dump_only=True)
    module = fields.String(dump_only=True)
    contact_type = fields.String(dump_only=True)
    company_name = fields.String(dump_only=True)


class CRMCommonConnectionReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "crm common contact" filters from request args
    """

    full_name = fields.String(load_only=True)
    company_name = fields.String(load_only=True)
    email = fields.String(load_only=True)
    contact_type = fields.String(load_only=True, validate=validate.OneOf(
        ACCOUNT.CRM_ACCT_TYPES))
    module = fields.String(load_only=True, validate=validate.OneOf(
        CRM.MODULE_TYPE))
    # operator
    operator = fields.String(validate=validate.OneOf(['and', 'or']),
                             missing='or')
    designation = fields.String(load_only=True)

