"""
Schemas for "crm distribution file library" related models
"""

from flask import g
from marshmallow import pre_dump, fields, validates_schema, ValidationError
from sqlalchemy import and_, or_

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.crm_resources.crm_distribution_file_library.models import \
    CRMDistributionLibraryFile


class CRMDistributionLibraryFileSchema(ma.ModelSchema):
    """
    Schema for loading "CRMDistributionLibraryFile" from request, and also
    formatting output
    """

    class Meta:
        model = CRMDistributionLibraryFile
        include_fk = True
        load_only = ('account_id', 'updated_by', 'created_by')
        dump_only = default_exclude + ('account_id', 'updated_by',
                                       'created_by',)
    file_url = ma.Url(dump_only=True)

    @pre_dump(pass_many=True)
    def loads_urls(self, objs, many):
        """
        Loads the urls of filename and thumbnail_name
        """
        if many:  # #TODO: write optimized load_url here instead?
            for obj in objs:
                obj.load_urls()
        else:
            objs.load_urls()


class CRMLibraryFileReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "crm library file" filters from request args
    """
    user_id = fields.Integer(load_only=True)
