"""
Schemas for "menu" related models
"""

from marshmallow_sqlalchemy import field_for
from marshmallow import (fields, ValidationError, post_load,
pre_load, validates, pre_dump)

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.menu.models import Menu


class MenuSchema(ma.ModelSchema):
    """
    Schema for loading "menu" from requests, and also formatting output
    """

    class Meta:
        model = Menu
        include_fk = True
        load_only = ('updated_by', 'created_by')
        dump_only = default_exclude + (
            'updated_by', 'created_by', 'parent_menu', 'child_menus', 'code')
        exclude = ('rolemenuperm', 'parent_menu')

    # relationships
    child_menus = ma.List(ma.Nested(
        'app.resources.menu.schemas.MenuSchema',
        dump_only=True))

    @pre_load
    def insert_sequence(self, data):
        if not self.instance and 'sequence' not in data:
            parent_id = None
            if 'parent_id' in data:
                parent_id = data['parent_id']
            menu_with_largest_seq = Menu.query.filter_by(
                parent_id=parent_id).order_by('-sequence').first()
            sequence = 1
            if menu_with_largest_seq:
                sequence = menu_with_largest_seq.sequence + 1
            data['sequence'] = sequence

    @validates('sequence')
    def validate_sequence(self, value):
        if not value or value <= 0:
            raise ValidationError('Sequence must be greater than 0.')

    @post_load
    def validate_parent_menu(self, data):
        if data.row_id and data.row_id == data.parent_id:
            raise ValidationError('Parent menu can not be self.')


class MenuCreateSchema(MenuSchema):
    class Meta:
        model = Menu
        include_fk = True
        load_only = ('updated_by', 'created_by')
        dump_only = default_exclude + (
            'updated_by', 'created_by', 'parent_menu', 'child_menus')
        exclude = ('rolemenuperm', 'parent_menu')


class MenuReadArgSchema(BaseReadArgsSchema):
    name = fields.String(load_only=True)
    parent_id = fields.Integer(load_only=True, missing=0)
    only_active = fields.Boolean(load_only=True, missing=True)