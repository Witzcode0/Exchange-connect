"""
Schemas for "reference project types" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.base import constants as APP
from app.toolkit_resources.ref_project_sub_child_type.models import RefProjectSubChildType


class RefProjectSubChildTypeSchema(ma.ModelSchema):

    class Meta:
        model = RefProjectSubChildType
        include_fk = True
        load_only = ('created_by', 'updated_by', 'child_id')
        dump_only = default_exclude + ('created_by', 'updated_by', 'child_id')

    ref_sub_parents = ma.Nested('app.toolkit_resources.ref_project_sub_type.schemas.RefProjectSubTypeSchema',
                                only=['row_id','parent_title'], dump_only=True)


class RefProjectSubChildTypeReadArgsSchema(BaseReadArgsSchema):

    project_type_id = fields.Integer(load_only=True)
    parent_id = fields.Integer(load_only=True)
    child_name = fields.String(load_only=True)