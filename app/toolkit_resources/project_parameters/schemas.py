"""
Schemas for "project parameters" related models
"""

from marshmallow import fields, validate, validates_schema, ValidationError
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.base import constants as APP
from app.toolkit_resources.project_parameters.models import ProjectParameter
from app.toolkit_resources.projects.models import Project
from app.toolkit_resources.ref_project_parameters.models import (
    RefProjectParameter)
from app.toolkit_resources.project_parameters import constants as PROJPARA


# project details that will be passed while populating project relation
project_fields = ['row_id', 'project_name', 'project_type_id', 'order_date',
                  'delivery_date']
# account details that will be passed while populating account relation
account_fields = ['row_id', 'links', 'account_name']


class ProjectParameterSchema(ma.ModelSchema):
    """
    Schema for loading "project parameter" from request,
     and also formatting output
    """

    # default fields to exclude from the schema for speed up
    _default_exclude_fields = ['project_files', 'project_screen_sharing']

    parent_parameter_name = field_for(
        ProjectParameter, 'parent_parameter_name',
        validate=[validate.Length(
                  min=1, error=APP.MSG_NON_EMPTY),
                  validate.Length(max=PROJPARA.NAME_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])
    parameter_name = field_for(
        ProjectParameter, 'parameter_name',
        validate=[validate.Length(
                  min=1, error=APP.MSG_NON_EMPTY),
                  validate.Length(max=PROJPARA.NAME_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])
    parameter_value = field_for(
        ProjectParameter, 'parameter_value',
        validate=[validate.Length(max=PROJPARA.NAME_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = ProjectParameter
        include_fk = True
        load_only = ('created_by', 'updated_by', 'account_id')
        dump_only = default_exclude + ('created_by', 'updated_by',
                                       'account_id')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('toolkit_api.projectparameterapi',
                          row_id='<row_id>'),
        'collection': ma.URLFor('toolkit_api.projectparameterlistapi')
    }, dump_only=True)

    project = ma.Nested(
        'app.toolkit_resources.projects.schemas.ProjectSchema',
        only=project_fields, dump_only=True)
    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True)
    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=['row_id'],
        dump_only=True)

    # maintain flag for validate parent parameter name.
    _validate_pp_name = False

    @validates_schema(pass_original=True)
    def validate_parent_parameter_name(self, data, original_data):
        """
        Validate Parent parameter name
        """
        error = False
        ref_proj_para_data = None
        model = None

        if self._validate_pp_name:
            if ('parent_parameter_name' in
                    original_data and original_data['parent_parameter_name']):
                # make query
                model = Project.query.filter(
                    Project.row_id == original_data['project_id']).first()
                if not model:
                    raise ValidationError(
                        'Project_id: %s does not exist' %
                        str(original_data['project_id']), 'project_id')
                # check parent parameter name exist or not
                ref_proj_para_data = RefProjectParameter.query.filter(
                    RefProjectParameter.project_type_id ==
                    model.project_type_id,
                    RefProjectParameter.parent_parameter_name ==
                    original_data['parent_parameter_name'],
                    RefProjectParameter.level ==
                    original_data['level']).first()
                if not ref_proj_para_data:
                    error = True
            if error:
                raise ValidationError(
                    'Parent parameter name: %s does not exist'
                    % original_data['parent_parameter_name'],
                    'parent_parameter_name'
                )


class ProjectParameterReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "project parameters" filters from request args
    """
    parameter_name = fields.String(load_only=True)
    parent_parameter_name = fields.String(load_only=True)
    project_id = fields.Integer(load_only=True)
