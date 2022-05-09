"""
Schemas for "news" related models
"""

from marshmallow import fields, validate

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.twitter_feeds.models import TwitterFeeds, TwitterFeedSource


class TwitterSourceFeedSchema(ma.ModelSchema):
    """
    Schema for loading "news item" from request, and also formatting
    output
    """

    class Meta:
        model = TwitterFeedSource
        include_fk = True
        dump_only = default_exclude + ('twitter_user_id', )


class TwitterFeedSchema(ma.ModelSchema):
    """
    Schema for loading "news item" from request, and also formatting
    output
    """

    class Meta:
        model = TwitterFeeds
        dump_only = default_exclude + ('domain_id', )


class TwitterFeedReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "news item" filters from request args
    """
    account_id = fields.Integer(load_only=True)
    following = fields.Boolean(load_only=True)
    screen_name = fields.String(load_only=True)
    full_name = fields.String(load_only=True)
    text = fields.String(load_only=True)

