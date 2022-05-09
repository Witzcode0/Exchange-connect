"""
Schemas for "permissions" related models
"""

from marshmallow import fields

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.permissions.models import Permission


class PermissionSchema(ma.ModelSchema):
    """
    Schema for loading "permission" from requests, and also formatting output
    """

    class Meta:
        model = Permission
        include_fk = True
        load_only = ('updated_by', 'created_by')
        dump_only = default_exclude + ('updated_by', 'created_by')


class PermissionEditSchema(PermissionSchema):
    """
    Schema for loading "permission" from requests at edit time
    """

    class Meta:
        dump_only = default_exclude + ('updated_by', 'created_by', 'code')


class PermissionReadArgSchema(BaseReadArgsSchema):
    name = fields.String(load_only=True)
    is_active = fields.Boolean(load_only=True)
