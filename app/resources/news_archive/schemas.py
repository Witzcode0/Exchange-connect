"""
Schemas for "news item archive" related models
"""

from marshmallow import fields, validate

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, account_fields)
from app.resources.news_archive.models import NewsItemArchive


# news details that will be passed while populating user relation
news_fields = ['row_id', 'links']


class NewsItemArchiveSchema(ma.ModelSchema):
    """
    Schema for loading "news item archive" from request, and also formatting
    output
    """

    class Meta:
        model = NewsItemArchive
        include_fk = True
        load_only = ('updated_by', 'created_by', 'account_id', 'news_id')
        dump_only = default_exclude + ('updated_by', 'created_by',
                                       'account_id', 'news_id')
        exclude = ('news_j', )

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.newsitemarchiveapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.newsitemarchivelistapi')
    }, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True)
    news = ma.Nested(
        'app.resources.news.schemas.NewsItemSchema', only=news_fields,
        dump_only=True)


class NewsItemArchiveReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "news item archive" filters from request args
    """
    sort_by = fields.List(fields.String(), load_only=True, missing=[
        'posted_at'])
    sort = fields.String(validate=validate.OneOf(['asc', 'dsc']),
                         missing='dsc')
    title = fields.String(load_only=True)
    tags = fields.String(load_only=True)
