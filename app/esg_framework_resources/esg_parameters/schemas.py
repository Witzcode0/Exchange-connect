"""
Schemas for "parameters" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.base import constants as APP
from app.esg_framework_resources.esg_parameters.models import ESGParameter
from app.esg_framework_resources.esg_parameters import constants as ESGPARAMETERS


# User Details
user_fields = ['row_id']


class ESGParameterSchema(ma.ModelSchema):
    """
    Schema for loading "parameter" from request, and also formatting output
    """

    # default fields to exclude from the schema for speed up
    _default_exclude_fields = ['sector_parameters', 'children']

    name = field_for(ESGParameter, 'name', validate=[validate.Length(
        min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=ESGPARAMETERS.NAME_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    parameter_index = field_for(ESGParameter, 'parameter_index', validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=ESGPARAMETERS.PAR_IND_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = ESGParameter
        include_fk = True
        load_only = ('created_by', 'updated_by')
        dump_only = default_exclude + ('created_by', 'updated_by')
        exclude = ('parameter_sort_index',)

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('esg_api.esgparameterapi', row_id='<row_id>'),
        'collection': ma.URLFor('esg_api.esgparameterlistapi')
    }, dump_only=True)
    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)

    children = ma.List(ma.Nested(
        'app.esg_framework_resources.esg_parameters.schemas.ESGParameterSchema',
        only=['name', 'parameter_parent_id', 'parameter_index',
              'parameter_sort_index', 'children', 'row_id'],
        dump_only=True))


class ESGParameterReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "parameter" filters from request args
    """
    name = fields.String(load_only=True)
    parameter_index = fields.String(load_only=True)
    parameter_parent_id = fields.Integer(load_only=True)
