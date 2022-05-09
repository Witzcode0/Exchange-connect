"""
Schemas for "industries" related models
"""
from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base import constants as APP
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.resources.industries.models import Industry
from app.resources.industries import constants as INDUSTRY


# sector fields
sector_fields = ['name']


class IndustrySchema(ma.ModelSchema):
    """
    Schema for loading "Industry" from requests, and also formatting output
    """

    # default fields to exclude from the schema for speed up
    _default_exclude_fields = ['account_profiles']

    name = field_for(Industry, 'name', validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=INDUSTRY.NAME_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = Industry
        include_fk = True
        load_only = ('updated_by', 'created_by')
        dump_only = default_exclude + ('updated_by', 'created_by')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.industryapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.industrylistapi')
    }, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    sector = ma.Nested(
        'app.resources.sectors.schemas.SectorSchema', only=sector_fields,
        dump_only=True)


class IndustryReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "Industry" filters from request args
    """
    name = fields.String(load_only=True)
    sector_id = fields.Integer(load_only=True)
