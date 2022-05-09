"""
Schemas for "cities" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base import constants as APP
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.cities.models import City
from app.resources.cities import constants as CITY


class CitySchema(ma.ModelSchema):
    """
    Schema for loading "cities" from requests, and also formatting output
    """

    # default fields to exclude from the schema for speed up
    _default_exclude_fields = ['corporate_access_events']

    city_name = field_for(City, 'city_name', validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=CITY.CITY_NAME_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = City
        include_fk = True
        load_only = ('updated_by', 'created_by', 'deleted')
        dump_only = default_exclude + ('updated_by', 'created_by', 'deleted')

    links = ma.Hyperlinks({
        'self': ma.URLFor('api.cityapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.citylistapi')
    }, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=['row_id'],
        dump_only=True)


class CityReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "cities" filters from request args
    """

    city_name = fields.String(load_only=True)
    country_id = fields.Integer(load_only=True)
    state_id = fields.Integer(load_only=True)
