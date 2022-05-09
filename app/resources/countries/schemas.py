"""
Schemas for "countries" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base import constants as APP
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.countries.models import Country
from app.resources.countries import constants as COUNTRY


class CountrySchema(ma.ModelSchema):
    """
    Schema for loading "countries" from requests, and also formatting output
    """

    # default fields to exclude from the schema for speed up
    _default_exclude_fields = ['corporate_access_events']

    country_name = field_for(Country, 'country_name', validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=COUNTRY.COUNTRY_NAME_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = Country
        include_fk = True
        load_only = ('updated_by', 'created_by', 'deleted')
        dump_only = default_exclude + ('updated_by', 'created_by', 'deleted')

    links = ma.Hyperlinks({
        'self': ma.URLFor('api.countryapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.countrylistapi')
    }, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=['row_id'],
        dump_only=True)


class CountryReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "countries" filters from request args
    """

    country_name = fields.String(load_only=True)
