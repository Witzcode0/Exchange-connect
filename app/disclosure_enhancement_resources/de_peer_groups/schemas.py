"""
Schemas for "Disclosure enhancement peer group" related models
"""

from marshmallow import fields, validates_schema, ValidationError
from sqlalchemy.orm import load_only

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.disclosure_enhancement_resources.de_peer_groups.models import (
    DePeerGroup)

from app.resources.companies.models import Company


# company Details
company_fields = ['row_id', 'company_name', 'sector_id', 'industry_id',
                  'country', 'identifier', 'isin_number', 'sedol', 'address',
                  'city', 'permanent_security_identifier']
# User Details
user_fields = ['row_id']


class DePeerGroupSchema(ma.ModelSchema):
    """
    Schema for loading "de_peer_group"
    from request, and also formatting output
    """

    company_ids = fields.List(fields.Integer(), dump_only=True)

    class Meta:
        model = DePeerGroup
        include_fk = True
        load_only = ('created_by', 'updated_by')
        dump_only = default_exclude + ('created_by', 'updated_by')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('disclosure_enhancement_api.depeergroupapi',
                          row_id='<row_id>'),
        'collection': ma.URLFor(
            'disclosure_enhancement_api.depeergrouplistapi')
    }, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    companies = ma.List(ma.Nested(
        'app.resources.companies.schemas.CompanySchema', only=company_fields))
    primary_company = ma.Nested(
        'app.resources.companies.schemas.CompanySchema',
        only=company_fields)

    @validates_schema(pass_original=True)
    def validate_company_ids(self, data, original_data):
        """
        Validate that the company_ids "company" exist
        """
        error = False
        missing = []
        self._cached_ids = []
        # load all the company ids
        c_ids = []
        if 'company_ids' in original_data and original_data['company_ids']:
            c_ids = original_data['company_ids'][:]
        # validate company_ids, and load all the _cached_ids
        if c_ids:
            # make query
            cids = []
            for c in c_ids:
                try:
                    cids.append(int(c))
                except Exception as e:
                    continue
            self._cached_ids = [c for c in Company.query.filter(
                Company.row_id.in_(cids)).options(load_only(
                    'row_id')).all()]
            company_ids = [c.row_id for c in self._cached_ids]
            missing = set(cids) - set(company_ids)
            if missing:
                error = True

        if error:
            raise ValidationError(
                'Company: %s do not exist' % missing,
                'company_ids'
            )


class DePeerGroupReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "de_peer_group" filters from request args
    """
    name = fields.String(load_only=True)
