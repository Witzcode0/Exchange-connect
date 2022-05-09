"""
Schemas for "domain_config" related models
"""

from marshmallow import fields

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.domain_resources.domain_config.models import DomainConfig


class DomainConfigSchema(ma.ModelSchema):
    """
    Schema for loading "domain_config" from request, and also formatting output
    """

    class Meta:
        model = DomainConfig
        include_fk = True
        load_only = ('deleted', 'updated_by', 'created_by')
        dump_only = default_exclude + ('updated_by', 'created_by')


class DomainConfigReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "domain_config" filters from request args
    """
    # standard db fields
    name = fields.String(load_only=True)
