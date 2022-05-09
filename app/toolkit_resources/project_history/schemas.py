"""
Schemas for "project_history" related models
"""
import json

from marshmallow import fields, validate, validates_schema, ValidationError
from marshmallow_sqlalchemy import field_for
from sqlalchemy.orm import load_only

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.base import constants as APP
from app.resources.users.models import User
from app.toolkit_resources.project_history.models import ProjectHistory
from app.toolkit_resources.projects import constants as PROJECT
from app.toolkit_resources.ref_project_parameters.models import (
    RefProjectParameter)
from app.toolkit_resources.project_parameters.models import ProjectParameter
from app.toolkit_resources.project_status.schemas import ProjectStatusSchema


# account details that will be passed while populating account relation
account_fields = ['row_id', 'links', 'account_name']
# project type details
proj_type_fields = ['row_id', 'project_type_name', 'estimated_delivery_days']
# project analysts details that will passed while
# populating project analyst relation
proj_analyst_fields = ['row_id', 'project_id', 'analyst_id']
proj_designer_fields = ['row_id', 'project_id', 'designer_id']
# user details that will be passed while populating user relation
analyst_user_fields = user_fields + ['email', 'profile.phone_number']
designer_user_fields = user_fields + ['email', 'profile.phone_number']
project_status_fields = ['row_id', 'sequence', 'name', 'code']
file_archive_fields = ['row_id', 'category', 'filename', 'file_major_type',
                       'remarks', 'file_type', 'file_url', 'version',
                       'is_approved']
file_creator_fields = ['creator.row_id', 'creator.email',
                       'creator.profile.first_name',
                       'creator.profile.last_name',
                       'creator.profile.designation']

class ProjectHistorySchema(ma.ModelSchema):
    """
    Schema for loading "project" from request, and also formatting output
    """

    # default fields to exclude from the schema for speed up
    _default_exclude_fields = []

    # project_name = field_for(Project, 'project_name', validate=[
    #     validate.Length(max=PROJECT.NAME_MAX_LENGTH,
    #                     error=APP.MSG_LENGTH_EXCEEDS)])
    # glossary = field_for(Project, 'glossary', validate=[validate.Length(
    #     max=PROJECT.NAME_MAX_LENGTH, error=APP.MSG_LENGTH_EXCEEDS)])
    # special_instructions = field_for(
    #     Project, 'special_instructions', validate=[validate.Length(
    #         max=PROJECT.INST_MAX_LENGTH, error=APP.MSG_LENGTH_EXCEEDS)])
    #
    # percentage = field_for(Project, 'percentage', as_string=True)
    # work_area = field_for(
    #     Project, 'work_area', validate=validate.OneOf(PROJECT.WORK_ARIAS))
    # dimention = field_for(
    #     Project, 'dimention', validate=validate.OneOf(PROJECT.DIMENTION_TYPES))
    # sides_nr = field_for(
    #     Project, 'sides_nr', validate=validate.Range(min=0))
    # slides_completed = field_for(
    #     Project, 'slides_completed', validate=validate.Range(min=0))

    class Meta:
        model = ProjectHistory
        include_fk = True
        load_only = ('created_by', 'updated_by', 'account_id')
        dump_only = default_exclude + (
            'created_by', 'updated_by', 'account_id', 'is_draft', 'deleted',
            'admin_id', 'is_completed')

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)

    project_type = ma.Nested(
        'app.toolkit_resources.ref_project_types.schemas.RefProjectTypeSchema',
        only=proj_type_fields, dump_only=True)
    status = ma.Nested(
        'app.toolkit_resources.project_status.schemas.ProjectStatusSchema',
        only=project_status_fields)


# class ProjectPutSchema(ProjectSchema):
#     """
#     Schema for extending project schema for using project_id as dump_only
#     in project put functionality
#     """
#     project_parameters = ma.List(ma.Nested(
#         'app.toolkit_resources.project_parameters.'
#         'schemas.ProjectParameterSchema',
#         exclude=['project_id', 'account', 'project', 'creator']),
#         dump_only=True)
#     project_parameter_delete_ids = fields.List(fields.Integer, load_only=True)
#
#     class Meta:
#         dump_only = default_exclude + (
#             'created_by', 'updated_by', 'account_id', 'is_draft', 'deleted',
#             'admin_id')


class ProjectHistoryReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "project" filters from request args
    """
    project_name = fields.String(load_only=True)
    project_id = fields.Integer(load_only=True)
    project_type_id = fields.Integer(load_only=True)
    is_completed = fields.Boolean(load_only=True)
    cancelled = fields.Boolean(load_only=True)
