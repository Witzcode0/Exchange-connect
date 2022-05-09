"""
Schemas for "market_comment" related models
"""

from marshmallow import fields

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.market_resources.market_comment.models import MarketAnalystComment

corporate_user_fields = user_fields + [
    'account.profile.profile_photo_url',
    'account.profile.profile_thumbnail_url', 'account.identifier']


class MarketanalystCommentSchema(ma.ModelSchema):
    """
    Schema for loading "market_comment" from request,\
    and also formatting output
    """
    _default_exclude_fields = []

    class Meta:
        model = MarketAnalystComment
        include_fk = True
        load_only = ('updated_by', 'created_by', )
        dump_only = default_exclude + ('updated_by', 'created_by')

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema',  only=corporate_user_fields,
        dump_only=True)
    domain = ma.Nested(
        'app.domain_resources.domains.schemas.DomainSchema', only=('row_id','country'),
        dump_only=True)


class MarketanalystCommentReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "Market comment" filters from request args
    """
    # standard db fields
    created_date = fields.Date(load_only=True)
