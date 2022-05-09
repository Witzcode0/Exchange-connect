"""
Schemas for "project screen sharing" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.base import constants as APP
from app.toolkit_resources.project_screen_sharings.models import (
    ProjectScreenSharing)
from app.toolkit_resources.project_screen_sharings import constants as \
    PROSCREENSHARE


class ProjectScreenSharingSchema(ma.ModelSchema):
    """
    Schema for loading "project screen sharing" from request,
    and also formatting output
    """
    remarks = field_for(ProjectScreenSharing, 'remarks', validate=[
        validate.Length(max=PROSCREENSHARE.REMARK_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = ProjectScreenSharing
        include_fk = True
        load_only = ('updated_by', 'account_id', 'created_by',)
        dump_only = default_exclude + ('updated_by', 'account_id',
                                       'created_by', 'sent_by')

    links = ma.Hyperlinks({
        'self': ma.URLFor(
            'toolkit_api.projectscreensharingapi', row_id='<row_id>'),
        'collection': ma.URLFor('toolkit_api.projectscreensharinglistapi')
    }, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    project_parameter = ma.Nested(
        'app.toolkit_resources.project_parameters.'
        'schemas.ProjectParameterSchema', dump_only=True)


class ProjectScreenSharingReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "project screen sharing" filters from request args
    """
    project_id = fields.Integer(load_only=True)
    sent_by = fields.Integer(load_only=True)
    scheduled_at = fields.String(load_only=True)
    account_id = fields.Integer(load_only=True)
