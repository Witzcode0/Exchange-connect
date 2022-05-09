"""
Schemas for "parsing file" related models
"""

from marshmallow import fields, pre_dump

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.semidocument_resources.parsing_files.models import ParsingFile


class ParsingFileSchema(ma.ModelSchema):
    """
    Schema for loading "parsing file" from request, and also
    formatting output
    """

    class Meta:
        model = ParsingFile
        include_fk = True
        load_only = ('deleted', 'account_id', 'updated_by', 'created_by', 'file_type')
        dump_only = default_exclude + ('account_id', 'updated_by', 'deleted',
                                       'created_by')

    file_url = ma.Url(dump_only=True)

    @pre_dump(pass_many=True)
    def loads_urls(self, objs, many):
        """
        Loads the urls of filename
        """
        call_load = False  # minor optimisation
        if any(phfield in self.fields.keys() for phfield in [
                'file_url', 'filename']):
            # call load urls only if the above fields are asked for
            call_load = True

        if many:  # #TODO: write optimized load_url here instead?
            for obj in objs:
                if call_load:
                    obj.load_urls()
        else:
            if call_load:
                objs.load_urls()


class ParsingFileReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "ArchiveFile" filters from request args
    """
    # standard db fields
    filename = fields.String(load_only=True)
    research_report_id = fields.Integer(load_only=True)
