"""
Schemas for "feeds" related models
"""

from marshmallow import fields, validate

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.feeds.models import FeedItem


class FeedItemSchema(ma.ModelSchema):
    """
    Schema for formatting output
    """

    class Meta:
        model = FeedItem
        include_fk = True
        load_only = ('deleted', 'updated_by', 'created_by', 'account_id')
        dump_only = default_exclude + ('updated_by', 'created_by',
                                       'account_id')
        exclude = ('post_date', 'poster_id')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.feeditemapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.feeditemlistapi')
    }, dump_only=True)
    # relations
    post = ma.Nested(
        'app.resources.posts.schemas.PostSchema', dump_only=True)
    # special starred status as object value to indicate if current_user
    # has already starred this feed item
    feed_starred = ma.Nested(
        'app.resources.post_stars.schemas.PostStarSchema',
        only=['row_id', 'links'], dump_only=True)
    # special commented status as object value to indicate if current_user
    # has already commented this feed item
    feed_commented = ma.Nested(
        'app.resources.post_comments.schemas.PostCommentSchema',
        only=['row_id', 'links'], dump_only=True)


class FeedItemReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "feed" filters from request args
    """
    sort_by = fields.List(
        fields.String(), load_only=True, missing=['post_date'])
    sort = fields.String(
        validate=validate.OneOf(['asc', 'dsc']), missing='dsc')
