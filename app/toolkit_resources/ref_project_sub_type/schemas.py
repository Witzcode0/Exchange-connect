"""
Schemas for "reference project types" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.base import constants as APP
from app.toolkit_resources.ref_project_sub_type.models import RefProjectSubType, ProjectSubParamGroup


class RefProjectSubTypeSchema(ma.ModelSchema):

    class Meta:
        model = RefProjectSubType
        include_fk = True
        load_only = ('created_by', 'updated_by', 'parent_id')
        dump_only = default_exclude + ('created_by', 'updated_by', 'parent_id')

    ref_child_parameters = ma.List(
        ma.Nested(
            'app.toolkit_resources.ref_project_sub_child_type.schemas.RefProjectSubChildTypeSchema',
            only=['row_id', 'child_title'], dump_only=True))


class ProjectSubParamGroupSchema(ma.ModelSchema):

    class Meta:
        model = ProjectSubParamGroup
        include_fk = True
        load_only = ('created_by', 'updated_by')
        dump_only = default_exclude + ('created_by', 'updated_by')

    ref_sub_parents = ma.Nested('app.toolkit_resources.ref_project_sub_type.schemas.RefProjectSubTypeSchema',
                                only=['parent_title'], dump_only=True)

    ref_sub_childs = ma.Nested('app.toolkit_resources.ref_project_sub_child_type.schemas.RefProjectSubChildTypeSchema',
                               only=['child_title'], dump_only=True)


class RefProjectSubTypeReadArgsSchema(BaseReadArgsSchema):

    project_type_id = fields.Integer(load_only=True)
    parent_title = fields.String(load_only=True)