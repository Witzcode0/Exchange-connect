"""
Schemas for "news wire post" related models
"""

from marshmallow import fields, validates_schema, ValidationError, validate
from sqlalchemy.orm import load_only

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, account_fields)
from app.newswire_resources.newswire_posts.models import NewswirePost
from app.newswire_resources.newswire_post_file_library.models import \
    NewswirePostLibraryFile
from app.newswire_resources.agency_pushes import constants as PLATFORM


# files details that will be passed while populating user relation
file_fields = ['row_id', 'filename', 'file_type', 'file_url', 'thumbnail_url']


class NewswirePostSchema(ma.ModelSchema):
    """
    Schema for loading "post" from request, and also formatting output
    """

    file_ids = fields.List(fields.Integer(), dump_only=True)
    platforms = fields.List(fields.String(validate=validate.OneOf(
        PLATFORM.AGPS_TYPES)))

    class Meta:
        model = NewswirePost
        include_fk = True
        load_only = ('deleted', 'updated_by', 'created_by', 'account_id')
        dump_only = default_exclude + ('updated_by', 'deleted', 'created_by',
                                       'account_id')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('newswire_api.newswirepostapi', row_id='<row_id>'),
        'collection': ma.URLFor('newswire_api.newswirepostlistapi')
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
        'app.newswire_resources.newswire_post_file_library.schemas.'
        'NewswirePostLibraryFileSchema', only=file_fields,
        dump_only=True))
    logo_file = ma.Nested(
        'app.newswire_resources.newswire_post_file_library.schemas.'
        'NewswirePostLibraryFileSchema', only=file_fields,
        dump_only=True)

    @validates_schema(pass_original=True)
    def validate_file_ids(self, data, original_data):
        """
        Validate that the file_ids "news wire post library file" exist
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
            self._cached_files = [
                f for f in NewswirePostLibraryFile.query.filter(
                    NewswirePostLibraryFile.row_id.in_(fids)).options(
                        load_only('row_id', 'deleted')).all() if not f.deleted]
            file_ids = [f.row_id for f in self._cached_files]
            missing = set(fids) - set(file_ids)
            if missing:
                error = True

        if error:
            raise ValidationError(
                'Files: %s do not exist' % missing, 'file_ids')


class NewswirePostReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "news wire post" filters from request args
    """
    heading = fields.String(load_only=True)
    company_name = fields.String(load_only=True)
    file_ids = fields.List(fields.Integer(), load_only=True)
