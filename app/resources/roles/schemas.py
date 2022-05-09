"""
Schemas for "role" related models
"""

from marshmallow import (
    fields, validate, post_dump, validates_schema, ValidationError, pre_dump)
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base import constants as APP
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.roles import constants as ROLE
from app.resources.roles.models import Role, RoleMenuPermission
from app.resources.permissions.models import Permission
from app.resources.permissions.schemas import PermissionSchema


class RoleSchema(ma.ModelSchema):
    """
    Schema for loading "role" from request, and also formatting output
    """

    """  *** for now adding of permissions is disabled
    permissions = field_for(
        Role, 'permissions', validate=validate.ContainsOnly(
            ROLE.USER_PERMISSIONS + ['']), missing=[])"""
    name = field_for(
        Role, 'name', validate=[validate.Length(
            min=1, error=APP.MSG_NON_EMPTY), validate.Length(
            max=ROLE.NAME_MAX_LENGTH, error=APP.MSG_LENGTH_EXCEEDS)])
    default = fields.Boolean(dump_only=True)

    class Meta:
        model = Role
        include_fk = True
        load_only = ('deleted', 'updated_by', 'created_by', 'users')
        dump_only = default_exclude + ('deleted', 'updated_by', 'created_by',
                                       'users', )
        exclude = ('rolemenuperm_j',)

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.roleapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.rolelist')
    }, dump_only=True)

    role_menu_permissions = ma.List(ma.Nested(
        'app.resources.roles.schemas.RoleMenuPermissionSchema',
        only=['permissions', 'menu'], dump_only=True))

    @post_dump(pass_many=True)
    def dump_perms(self, objs, many):
        """
        Dumps the permissions of the role
        """
        if not many:
            if ('role_menu_permissions' in objs
                    and objs['role_menu_permissions']):
                perm_schema = PermissionSchema(
                    only=['row_id', 'sequence', 'name', 'code'])
                for each in objs['role_menu_permissions']:
                    permissions = []
                    if (hasattr(self, 'need_all_permissions') and
                            self.need_all_permissions):
                        for permission_id in each['permissions']:
                            permission = Permission.query.get(permission_id)
                            if permission and permission.is_active:
                                permission = perm_schema.dump(
                                    permission)
                                permissions.append(permission.data)
                    each['permission_ids'] = each['permissions']
                    each['permissions'] = permissions

    @pre_dump(pass_many=True)
    def load_default(self, objs, many):
        if many:
            for obj in objs:
                obj.load_dynamic_properties()
        else:
            objs.load_dynamic_properties()


class RoleMenuPermissionSchema(ma.ModelSchema):
    class Meta:
        model = RoleMenuPermission
        include_fk = True
        load_only = ('updated_by', 'created_by')
        dump_only = default_exclude + ('updated_by', 'created_by', 'role')

    menu = ma.Nested(
        'app.resources.menu.schemas.MenuSchema',
        only=['row_id', 'name'], dump_only=True)

    roles = ma.Nested(
        'app.resources.role.schemas.RoleSchema',
        only=['row_id'], dump_only=True)

    @validates_schema
    def validate_permissions(self, data):
        for permission_id in data['permissions']:
            permission = Permission.query.get(permission_id)
            if not permission:
                raise ValidationError(
                    "permission with id {} doesn't exist".format(
                        permission_id))


class RoleReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "role" filters from request args
    """

    # standard db fields
    name = fields.String(load_only=True)
    permissions = fields.String(
        load_only=True,
        validate=validate.ContainsOnly(ROLE.USER_PERMISSIONS))