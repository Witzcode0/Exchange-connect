"""
Schemas for "post file library" related models
"""

from marshmallow import pre_dump

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.post_file_library.models import PostLibraryFile


class PostLibraryFileSchema(ma.ModelSchema):
    """
    Schema for loading "PostLibraryFile" from request, and also
    formatting output
    """

    class Meta:
        model = PostLibraryFile
        include_fk = True
        load_only = ('deleted', 'account_id', 'updated_by', 'created_by')
        dump_only = default_exclude + ('account_id', 'updated_by', 'deleted',
                                       'created_by', 'file_major_type')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.postlibraryfileapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.postlibraryfilelistapi')
    }, dump_only=True)

    file_url = ma.Url(dump_only=True)
    thumbnail_url = ma.Url(dump_only=True)

    @pre_dump(pass_many=True)
    def loads_urls(self, objs, many):
        """
        Loads the urls of filename and thumbnail_name
        """
        call_load = False  # minor optimisation
        thumbnail_only = False  # default thumbnail
        if any(phfield in self.fields.keys() for phfield in [
                'file_url', 'filename',
                'thumbnail_url', 'thumbnail_name']):
            # call load urls only if the above fields are asked for
            call_load = True
            if all(phfield not in self.fields.keys() for phfield in [
                    'file_url', 'filename']):
                thumbnail_only = True

        if many:  # #TODO: write optimized load_url here instead?
            for obj in objs:
                if call_load:
                    obj.load_urls(thumbnail_only=thumbnail_only)
        else:
            if call_load:
                objs.load_urls(thumbnail_only=thumbnail_only)


class PostLibraryFileReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "post library file" filters from request args
    """
    pass
