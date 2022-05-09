"""
Models for "role" package.
"""

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString, ChoiceString
from app.resources.roles import constants as ROLE
from app.resources.accounts import constants as ACCT


class Role(BaseModel):

    __tablename__ = 'role'

    name = db.Column(LCString(128), unique=True, nullable=False)
    permissions = db.Column(db.ARRAY(ChoiceString(
        ROLE.USER_PERMISSIONS_CHOICES)), nullable=False)

    created_by = db.Column(db.BigInteger, nullable=False)
    updated_by = db.Column(db.BigInteger, nullable=False)

    # deleted bit
    deleted = db.Column(db.Boolean, default=False)
    account_type = db.Column(ChoiceString(
        ACCT.ACCT_TYPES_CHOICES))
    is_active = db.Column(db.Boolean, default=True)
    sequence = db.Column(db.Integer)
    description = db.Column(db.String(256))

    role_menu_permissions = db.relationship(
        'RoleMenuPermission', backref=db.backref(
            'role', uselist=True),
        foreign_keys="[RoleMenuPermission.role_id]",
        primaryjoin="Role.row_id==RoleMenuPermission.role_id",
        passive_deletes=True)

    def __init__(self, name=None, permissions=None, created_by=None,
                 updated_by=None, *args, **kwargs):

        self.name = name
        self.permissions = permissions
        self.created_by = created_by
        self.updated_by = updated_by
        super(Role, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Role %r>' % (self.name)

    def is_default(self):
        """
        Whether this is a default "system" role, i.e which have been defined
        in code, and cannot be changed.
        """
        if self.name in ROLE.ROLES:
            return True
        return False
    def load_dynamic_properties(self):
        self.default = self.is_default()


class RoleMenuPermission(BaseModel):

    __tablename__ = 'role_menu_permissions'

    role_id = db.Column(db.BigInteger, db.ForeignKey(
        'role.id', name='role_menu_permissions_role_id_fkey',
        ondelete='CASCADE'),
        nullable=False)
    menu_id = db.Column(db.BigInteger, db.ForeignKey(
        'menu.id', name='role_menu_permissions_menu_id_fkey',
        ondelete='CASCADE'), nullable=False)
    permissions = db.Column(db.ARRAY(db.BigInteger), nullable=False)

    menu = db.relationship(
        'Menu', backref=db.backref(
            'rolemenuperm', lazy='dynamic',cascade='all'))

    def __init__(self, created_by=None,
                 updated_by=None, *args, **kwargs):

        self.created_by = created_by
        self.updated_by = updated_by
        super(RoleMenuPermission, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<RoleMenuPermission %r>' % (self.role_id)

