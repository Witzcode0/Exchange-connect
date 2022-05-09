"""
helpers for menu module
"""
from app.resources.menu.models import Menu
from app.resources.menu.schemas import MenuSchema


def load_child_menu_objects(parent_menus):
    """

    :param parent_menu: list of menu dictionarys
    :return: menu models, errors
    all descendants of parent menu will be loaded in schema
    for updating the sequences
    """
    menu_objs = []
    errors = []
    menu_schema = MenuSchema()

    def _menu_recursive(menus):
        for menu in menus:
            model = Menu.query.get(menu['row_id'])
            if not model:
                continue
            data, error = menu_schema.load(
                menu, instance=model, partial=True)
            if not error:
                menu_objs.append(data)
            else:
                errors.append(error)
            if 'child_menus' in menu and menu['child_menus']:
                _menu_recursive(menu['child_menus'])

    _menu_recursive(parent_menus)

    return menu_objs, errors


def keep_only_active_menus(menus):
    menus_cnt = len(menus)
    i = 0
    while i < menus_cnt:
        try:
            popped = False
            if not menus[i]['is_active']:
                menus.pop(i)
                popped = True
            if not popped:
                if menus[i]['child_menus']:
                    keep_only_active_menus(menus[i]['child_menus'])
                i += 1
        except IndexError:
            break
