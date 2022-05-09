"""
Schemas for "post stars" related models
"""

from marshmallow import fields, pre_dump, validate, validates_schema,\
    ValidationError

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, account_fields)
from app.resources.post_stars.models import PostStar


post_fields = ['row_id', 'title', 'description', 'created_by', 'account_id']


class PostStarSchema(ma.ModelSchema):
    """
    Schema for loading "post star" from request, and also formatting output
    """

    class Meta:
        model = PostStar
        include_fk = True
        load_only = ('updated_by', 'created_by', 'account_id')
        dump_only = default_exclude + (
            'updated_by', 'created_by', 'account_id')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.poststarapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.poststarlistapi')
    }, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True)
    post = ma.Nested(
        'app.resources.posts.schemas.PostSchema', only=post_fields,
        dump_only=True)


class PostStarReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "Post Comment" filters from request args
    """

    post_id = fields.Integer()
