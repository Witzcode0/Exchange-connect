"""
Schemas for "descriptor_master" related models
"""
from marshmallow import fields
from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.descriptor.models import BSE_Descriptor
# from app.resources.bse.models import BSE_Descriptor
from app.resources.bse.schemas import BseDescriptorSchema

# class BseDescriptorSchema(ma.ModelSchema):
#     """
#     Schema for loading data from BSE_Descriptor
#     """
#     class Meta:
#         model = BSE_Descriptor
#         include_fk = True
#         load_only = ('deleted', 'updated_by', 'created_by')
#         dump_only = default_exclude + ('updated_by', 'deleted', 'created_by')


class AdminBseDescriptorSchema(BseDescriptorSchema):

    class Meta:
        model = BSE_Descriptor
        include_fk = True
        load_only = ('deleted', 'updated_by', 'created_by')
        dump_only = default_exclude + (
            'updated_by', 'deleted', 'created_by', 'name')

    category = ma.Nested(
        'app.resources.corporate_announcements_category.schemas.CorporateAnnouncementCategorySchema',
        only=['name', 'row_id'],
        dump_only=True)


class BseDescriptorReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "descriptor" filters from request args
    """
    descriptor_name = fields.String(load_only=True)
    # sort_by = fields.List(fields.String(), load_only=True)
    # pass