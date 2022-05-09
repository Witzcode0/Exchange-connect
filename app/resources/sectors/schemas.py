"""
Schemas for "sectors" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.base import constants as APP
from app.resources.sectors.models import Sector
from app.resources.sectors import constants as SECTOR

#  user details that will be passed while populating user relation
user_fields = ['row_id']


class SectorSchema(ma.ModelSchema):
    """
    Schema for loading "sector" from request, and also formatting output
    """

    # default fields to exclude from the schema for speed up
    _default_exclude_fields = ['account_profiles', 'industries']

    name = field_for(Sector, 'name', validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=SECTOR.NAME_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = Sector
        load_only = ('updated_by', 'created_by')
        dump_only = default_exclude + ('created_by', 'updated_by')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.sectorapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.sectorlistapi')
    }, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)


class SectorReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "sector" filters from request args
    """

    name = fields.String(load_only=True)
