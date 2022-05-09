"""
Schemas for "project_designers" related models
"""

from marshmallow import fields

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.toolkit_resources.project_designers.models import ProjectDesigner


# designer user details that will be passed while populating user relation
designer_user_fields = user_fields + ['email', 'profile.phone_number']


class ProjectDesignerSchema(ma.ModelSchema):
    """
    Schema for loading "project_designer" from request,\
    and also formatting output
    """
    class Meta:
        model = ProjectDesigner
        include_fk = True
        load_only = ('updated_by', 'created_by')
        dump_only = default_exclude + ('created_by', 'updated_by')

    designed_project = ma.Nested(
        'app.toolkit_resources.projects.schemas.ProjectSchema',
        only=['row_id'], dump_only=True)
    designer = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=designer_user_fields,
        dump_only=True)


class ProjectDesignerReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "project_designer" filters from request args
    """
    project_id = fields.Integer(load_only=True)
    designer_id = fields.Integer(load_only=True)
