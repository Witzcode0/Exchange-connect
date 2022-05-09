"""
Schemas for "news" related models
"""

from marshmallow import fields, validate

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.news.models import NewsSource, NewsItem, TopNews
from app.resources.news import constants as NEWS
from marshmallow import (fields, validate, pre_dump, post_dump, validates_schema,
                         ValidationError)
from sqlalchemy import and_, or_


class NewsSourceSchema(ma.ModelSchema):
    """
    Schema for loading "news source" from request, and also formatting
    output
    """

    class Meta:
        model = NewsSource
        dump_only = default_exclude

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.newssourceapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.newssourcelistapi')
    }, dump_only=True)


class NewsItemSchema(ma.ModelSchema):
    """
    Schema for loading "news item" from request, and also formatting
    output
    """

    class Meta:
        model = NewsItem
        dump_only = default_exclude
        exclude = ('accounts',)

    # extra fields for output
    links = ma.Hyperlinks({
        'collection': ma.URLFor('api.newsitemlistapi')
    }, dump_only=True)

    # special archived status as object value to indicate if current_user
    # has already archived this news item
    news_archived = ma.Nested(
        'app.resources.news_archive.schemas.NewsItemArchiveSchema',
        only=['row_id', 'links'], dump_only=True)


class NewsItemReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "news item" filters from request args
    """
    sort_by = fields.List(fields.String(), load_only=True, missing=[
        'posted_at'])
    sort = fields.String(validate=validate.OneOf(['asc', 'dsc']),
                         missing='dsc')
    title = fields.String(load_only=True)
    tags = fields.String(load_only=True,
                         validate=validate.OneOf(NEWS.NEWS_TAGS))
    account_id = fields.Integer(load_only=True)
    following = fields.Boolean(load_only=True)


class TopNewsSchema(ma.ModelSchema):
    """
    Schema for loading "top news" from request, and also formatting
    """
    class Meta:
        model = TopNews
        include_fk = True
        load_only = ('updated_by', 'created_by',)
        dump_only = ('updated_by', 'created_by')

    @post_dump
    def load_news_ids(self, obj):
        """
        add news object in response
        """
        obj['news'] = []
        for i in NewsItem.query.filter(NewsItem.row_id.in_(obj['news_ids'])).all():
            obj['news'].append({'row_id':i.row_id,'news_title':i.title,
                'description':str(i.description),'posted_at':str(i.posted_at),
                'news_name':str(i.news_name),'link':str(i.link)})


class TopNewsReadArgSchema(BaseReadArgsSchema):
    """
    Schema for reading "top news" filters from request args
    """

    from_date = fields.Date(load_only=True)
    to_date = fields.Date(load_only=True)
