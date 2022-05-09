"""
Schemas for "posts" related models
"""

from marshmallow import fields, validates_schema, ValidationError, pre_dump
from sqlalchemy.orm import load_only

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, account_fields)
from app.resources.posts.models import Post
from app.resources.post_file_library.models import PostLibraryFile


# files details that will be passed while populating user relation
file_fields = ['row_id', 'filename', 'file_type', 'file_url', 'thumbnail_url']


class SharedUrlPreviewSchema(ma.Schema):
    """
    Schema for loading "shared url preview" details from request,
    and also formatting output
    """

    image = fields.Url()
    title = fields.String()
    description = fields.String()
    reference_url = fields.Url()


class PostSchema(ma.ModelSchema):
    """
    Schema for loading "post" from request, and also formatting output
    """

    # default fields to exclude from the schema for speed up
    _default_exclude_fields = ['feeds']

    file_ids = fields.List(fields.Integer(), dump_only=True)
    shared_url_preview = fields.Nested(SharedUrlPreviewSchema)

    class Meta:
        model = Post
        include_fk = True
        load_only = ('deleted', 'updated_by', 'created_by', 'account_id')
        # #TODO: slug used in future
        dump_only = default_exclude + ('updated_by', 'deleted', 'created_by',
                                       'account_id', 'slug', 'shared')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.postapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.postlistapi')
    }, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    editor = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True)
    files = ma.List(ma.Nested(
        'app.resources.post_file_library.schemas.PostLibraryFileSchema',
        only=['row_id', 'filename', 'file_type', 'file_major_type',
              'file_url', 'thumbnail_url'], dump_only=True))
    shared_post = ma.Nested(
        'app.resources.posts.schemas.PostSchema',
        exclude=['shared_post', 'post_starred', 'post_commented'],
        dump_only=True)
    # special starred status as object value to indicate if current_user
    # has already starred this news item
    post_starred = ma.Nested(
        'app.resources.post_stars.schemas.PostStarSchema',
        only=['row_id', 'links'], dump_only=True)
    # special commented status as object value to indicate if current_user
    # has already commented this news item
    post_commented = ma.Nested(
        'app.resources.post_comments.schemas.PostCommentSchema',
        only=['row_id', 'links'], dump_only=True)

    @validates_schema(pass_original=True)
    def validate_file_ids(self, data, original_data):
        """
        Validate that the file_ids "post library file" exist
        """
        error = False
        missing = []
        self._cached_files = []
        # load all the file ids
        f_ids = []
        if 'file_ids' in original_data and original_data['file_ids']:
            f_ids = original_data['file_ids'][:]
        # validate file_ids, and load all the _cached_files
        if f_ids:
            # make query
            fids = []
            for f in f_ids:
                try:
                    fids.append(int(f))
                except Exception as e:
                    continue
            self._cached_files = [f for f in PostLibraryFile.query.filter(
                PostLibraryFile.row_id.in_(fids)).options(load_only(
                    'row_id', 'deleted')).all() if not f.deleted]
            file_ids = [f.row_id for f in self._cached_files]
            missing = set(fids) - set(file_ids)
            if missing:
                error = True

        if error:
            raise ValidationError(
                'Files: %s do not exist' % missing,
                'file_ids'
            )


class PostReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "Post" filters from request args
    """
    title = fields.String(load_only=True)


class AdminPostReadArgsSchema(PostReadArgsSchema):
    """
    Schema for reading "Admin Post" filters from request args
    """
    account_id = fields.Integer(load_only=True)
    created_by = fields.Integer(load_only=True)
