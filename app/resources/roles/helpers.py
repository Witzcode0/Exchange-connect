"""
helper functions for roles
"""

from app.resources.roles.schemas import RoleMenuPermissionSchema
from app.resources.permissions.models import Permission


def get_role_menu_perms_object(role_id, menus):
    """

    :param role_id: Integer
    :param menus: list of menu dictionaries
    :return: role_menu_permissions models
    """
    role_menu_perms = []
    json_data = {
        'role_id': role_id,
        'menu_id': None,
        'permissions': None
    }
    rmp_schema = RoleMenuPermissionSchema()

    def _get_role_menu_perms_object(menu_list):
        for menu in menu_list:
            if 'is_visible' in menu and not menu['is_visible']:
                continue
            if menu['permission_ids']:
                json_data['menu_id'] = menu['row_id']
                json_data['permissions'] = menu['permission_ids']
                data, errors = rmp_schema.load(json_data)
                if not errors:
                    role_menu_perms.append(data)
            if menu['child_menus']:
                _get_role_menu_perms_object(menu['child_menus'])

    _get_role_menu_perms_object(menus)

    return role_menu_perms


def add_permissions_to_menus(
        menus, perms, include_all_menus=True, is_first_time=True,
        include_all_perm=False):
    # will add permissions in mutable menu object recursively
    menu_perms = perms
    if is_first_time:
        menu_perms = {}
        all_perms = {}
        if include_all_perm:
            permissions = Permission.query.all()
            for permission in permissions:
                all_perms[permission.row_id] = permission.code

        for permitted in perms:
            menu_id = permitted['menu']['row_id']
            menu_perms[menu_id] = {
                'permissions': permitted['permissions'],
                'permission_ids': permitted['permission_ids']}
            if include_all_perm:
                all_permissions = {}
                for perm_id, code in all_perms.items():
                    all_permissions[code] = False
                    if perm_id in permitted['permission_ids']:
                        all_permissions[code] = True
                menu_perms[menu_id]['permissions'] = all_permissions

    menu_cnt = len(menus)
    cnt = 0
    while cnt < menu_cnt:
        try:
            popped = False
            menus[cnt]['permissions'] = []
            menus[cnt]['permission_ids'] = []
            if menus[cnt]['row_id'] in menu_perms:
                menus[cnt]['permissions'] = \
                    menu_perms[menus[cnt]['row_id']]['permissions']
                menus[cnt]['permission_ids'] = \
                    menu_perms[menus[cnt]['row_id']]['permission_ids']
            elif not include_all_menus:
                menus.pop(cnt)
                popped = True

            if not popped:
                if 'child_menus' in menus[cnt]:
                    add_permissions_to_menus(
                        menus[cnt]['child_menus'], menu_perms,
                        include_all_menus, False, include_all_perm)
                cnt += 1
        except IndexError:
            break
