"""
Schemas for "domain" related models
"""

from marshmallow import (
    fields, validate, pre_load, post_dump, validates_schema, ValidationError)
from marshmallow_sqlalchemy import field_for
from marshmallow import ValidationError

from app import ma
from app.base import constants as APP
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.domain_resources.domains.models import Domain


class DomainSchema(ma.ModelSchema):
    """
    Schema for loading "domain" from request, and also formatting output
    """
    name = field_for(Domain, 'name', validate=[
        validate.Length(min=5, error=APP.MSG_NON_EMPTY)])

    class Meta:
        model = Domain
        include_fk = True
        load_only = ('deleted', 'updated_by', 'created_by')
        dump_only = default_exclude + ('updated_by', 'created_by' ,'domain_configs')
        exclude = ('accounts', 'registration_requests', 'news_sources',
                   'news_items', 'twitter_sources', 'tweets')

    domain_configs = ma.List(ma.Nested(
        'app.domain_resources.domain_config.schemas.DomainConfigSchema'))

    @pre_load
    def check_domain(self, data):
        if "name" in data and '://' in data["name"]:
            raise ValidationError("Invalid domain name. Valid format name.com")


class DomainReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "domain" filters from request args
    """
    # standard db fields
    name = fields.String(load_only=True)
    country = fields.String(load_only=True)
