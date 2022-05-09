"""
Schemas for "market_performance" related models
"""

from marshmallow import fields, validate

from app import ma
from app.base import constants as APP
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.market_resources.market_performance.models import MarketPerformance
from marshmallow_sqlalchemy import field_for

corporate_user_fields = user_fields + [
    'account.profile.profile_photo_url',
    'account.profile.profile_thumbnail_url', 'account.identifier']


class MarketPerformanceSchema(ma.ModelSchema):
    """
    Schema for loading "market_performance" from request,\
    and also formatting output
    """
    _default_exclude_fields = []

    class Meta:
        model = MarketPerformance
        include_fk = True
        load_only = ('updated_by', 'created_by', )
        dump_only = default_exclude + ('updated_by', 'created_by')

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema',  only=corporate_user_fields,
        dump_only=True)


class MarketPerformanceReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "Market Performance" filters from request args
    """
    # standard db fields
    created_date = fields.Date(load_only=True)
    account_id = fields.Integer(load_only=True)
    account_sort_name = fields.String(load_only=True)
