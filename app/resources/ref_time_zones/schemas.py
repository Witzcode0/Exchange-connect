"""
Schemas for "time zone" related models
"""

from marshmallow import fields

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.ref_time_zones.models import RefTimeZone


class RefTimeZoneSchema(ma.ModelSchema):
    """
    Schema for loading "time zone" from request, and also formatting output
    """

    class Meta:
        model = RefTimeZone
        include_fk = True
        load_only = ('updated_by', 'created_by')
        dump_only = default_exclude + ('updated_by', 'created_by')

    # extra fields for output
    links = ma.Hyperlinks({
        'collection': ma.URLFor('api.reftimezonelistapi')
    }, dump_only=True)


class RefTimeZoneReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "time zone" filters from request args
    """
    display_value = fields.String(load_only=True)
