"""
Schemas for "post comment" related models
"""

from marshmallow import (
    fields, pre_dump, validate, validates_schema, ValidationError)
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, account_fields)
from app.base import constants as APP
from app.resources.post_comments.models import PostComment
from app.resources.post_comments import constants as POSTCOMMENT


post_fields = ['row_id', 'title', 'description']


class PostCommentSchema(ma.ModelSchema):
    """
    Schema for loading "post Comment" from request, and also formatting output
    """
    message = field_for(PostComment, 'message', validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=POSTCOMMENT.MESSAGE_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = PostComment
        include_fk = True
        load_only = ('deleted', 'updated_by', 'created_by', 'account_id')
        dump_only = default_exclude + ('updated_by', 'deleted', 'created_by',
                                       'account_id')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.postcommentapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.postcommentlistapi')
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
    # #TODO: may be used in future
    # post_commented = ma.Nested(
    #     'app.resources.post_comments.schemas.PostCommentSchema',
    #     dump_only=True)

    @validates_schema(pass_original=True)
    def validate_in_reply_to_comment_post_id_exists(self, data, original_data):
        """
        Validate that "in_reply_to" post comment post id exists
        """
        error = False
        if 'in_reply_to' in data:
            post_comment_data = PostComment.query.filter(
                PostComment.row_id == data['in_reply_to']).first()
            if post_comment_data:
                if post_comment_data.post_id != data['post_id']:
                    error = True
        if error:
            raise ValidationError(
                "You can't reply to another post")


class PostCommentReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "Post Comment" filters from request args
    """
    post_id = fields.Integer(required=True)
    message = fields.String(load_only=True)
