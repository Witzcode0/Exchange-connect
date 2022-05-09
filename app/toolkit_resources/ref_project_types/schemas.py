"""
Schemas for "reference project types" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.base import constants as APP
from app.toolkit_resources.ref_project_types import (
    constants as REFPROJECTTYPES)
from app.toolkit_resources.ref_project_types.models import RefProjectType


class RefProjectTypeSchema(ma.ModelSchema):
    """
    Schema for loading "reference project types" from request,
    and also formatting output
    """

    # default fields to exclude from the schema for speed up
    _default_exclude_fields = ['projects', 'ref_project_parameters', ]

    project_type_name = field_for(
        RefProjectType, 'project_type_name', validate=[
            validate.Length(min=1, error=APP.MSG_NON_EMPTY),
            validate.Length(max=REFPROJECTTYPES.PROJECT_TYPE_NAME_MAX_LENGTH,
                            error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = RefProjectType
        include_fk = True
        load_only = ('created_by', 'updated_by')
        dump_only = default_exclude + ('created_by', 'updated_by')
        exclude = ('project_historys',)

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('toolkit_api.refprojecttypeapi', row_id='<row_id>'),
        'collection': ma.URLFor('toolkit_api.refprojecttypelistapi')
    }, dump_only=True)


class RefProjectTypeReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "reference project types" filters from request args
    """
    project_type_name = fields.String(load_only=True)
    estimated_delivery_days = fields.Integer(load_only=True)
    is_active = fields.Boolean(load_only=True, missing=True)
