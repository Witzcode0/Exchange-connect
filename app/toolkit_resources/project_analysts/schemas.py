"""
Schemas for "project_analysts" related models
"""

from marshmallow import fields

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.toolkit_resources.project_analysts.models import ProjectAnalyst


# analyst user details that will be passed while populating user relation
analyst_user_fields = user_fields + ['email', 'profile.phone_number']


class ProjectAnalystSchema(ma.ModelSchema):
    """
    Schema for loading "project_analyst" from request,\
    and also formatting output
    """
    class Meta:
        model = ProjectAnalyst
        include_fk = True
        load_only = ('updated_by', 'created_by')
        dump_only = default_exclude + ('created_by', 'updated_by')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('toolkit_api.projectanalystapi', row_id='<row_id>'),
        'collection': ma.URLFor('toolkit_api.projectanalystlistapi')
    }, dump_only=True)

    assigned_project = ma.Nested(
        'app.toolkit_resources.projects.schemas.ProjectSchema',
        only=['row_id'], dump_only=True)
    analyst = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=analyst_user_fields,
        dump_only=True)


class ProjectAnalystReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "project_analyst" filters from request args
    """
    project_id = fields.Integer(load_only=True)
    analyst_id = fields.Integer(load_only=True)
