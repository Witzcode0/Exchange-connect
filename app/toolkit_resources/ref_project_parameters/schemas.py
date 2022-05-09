"""
Schemas for "reference project parameters" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.base import constants as APP
from app.toolkit_resources.ref_project_parameters import (
    constants as REFPROJECTPARAMETERS)
from app.toolkit_resources.ref_project_parameters.models import (
    RefProjectParameter)


class RefProjectParameterSchema(ma.ModelSchema):
    """
    Schema for loading "reference project parameters" from request,
    and also formatting output
    """
    parent_parameter_name = field_for(
        RefProjectParameter, 'parent_parameter_name', validate=[
            validate.Length(min=1, error=APP.MSG_NON_EMPTY),
            validate.Length(
                max=REFPROJECTPARAMETERS.PARENT_PARAMETER_NAME_MAX_LENGTH,
                error=APP.MSG_LENGTH_EXCEEDS)])
    parameter_name = field_for(
        RefProjectParameter, 'parameter_name', validate=[
            validate.Length(min=1, error=APP.MSG_NON_EMPTY),
            validate.Length(
                max=REFPROJECTPARAMETERS.PARAMETER_NAME_MAX_LENGTH,
                error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = RefProjectParameter
        include_fk = True
        load_only = ('created_by', 'updated_by')
        dump_only = default_exclude + ('created_by', 'updated_by')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor(
            'toolkit_api.refprojectparameterapi', row_id='<row_id>'),
        'collection': ma.URLFor('toolkit_api.refprojectparameterlistapi')
    }, dump_only=True)

    ref_project_type = ma.Nested(
        'app.toolkit_resources.ref_project_types.schemas.RefProjectTypeSchema',
        dump_only=True)


class RefProjectParameterReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "reference project parameters" filters from request args
    """
    project_type_id = fields.Integer(load_only=True)
    parent_parameter_name = fields.String(load_only=True)
    parameter_name = fields.String(load_only=True)
