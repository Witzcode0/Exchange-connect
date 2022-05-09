"""
Schemas for "project_status" related models
"""

from marshmallow import fields, validate, validates_schema, ValidationError
from marshmallow_sqlalchemy import field_for
from sqlalchemy.orm import load_only

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.toolkit_resources.project_status.models import ProjectStatus
from app.base import constants as APP
from app.resources.users.models import User
from app.toolkit_resources.projects.models import Project
from app.toolkit_resources.projects import constants as PROJECT
from app.toolkit_resources.ref_project_parameters.models import (
    RefProjectParameter)
from app.toolkit_resources.project_parameters.models import ProjectParameter


class ProjectStatusSchema(ma.ModelSchema):
    """
    Schema for loading "project" from request, and also formatting output
    """

    class Meta:
        model = ProjectStatus
        include_fk = True
        dump_only = default_exclude + ('code',)
        exclude = ('projects', 'created_by', 'updated_by', 'project_historys')


class ProjectStatusReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "project_designer" filters from request args
    """
    name = fields.String(load_only=True)
