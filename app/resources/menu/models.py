"""
Models for "menu" package.
"""

from app import db
from app.base.models import BaseModel
from sqlalchemy import UniqueConstraint


class Menu(BaseModel):

    __tablename__ = 'menu'

    name = db.Column(db.String(256), nullable=False)
    front_end_url = db.Column(db.String(1024), nullable=False)
    parent_id = db.Column(db.BigInteger, db.ForeignKey(
        'menu.id', name='menu_parent_id_fkey', ondelete='CASCADE'))
    is_active = db.Column(db.Boolean, default=True)
    sequence = db.Column(db.Integer)
    description = db.Column(db.String(256))
    icon_name = db.Column(db.String(48))
    code = db.Column(db.String(64), nullable=False, unique=True)

    __table_args__ = (
        UniqueConstraint('parent_id', 'name',
                         name='menu_parent_id_name_key'),
    )

    def __init__(self, *args, **kwargs):
        super(Menu, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Menu row_id=%r, name=%r>' % (
            self.row_id, self.name)

    child_menus = db.relationship(
        'Menu', backref=db.backref(
            'parent_menu', remote_side='Menu.row_id', uselist=True
            ), passive_deletes=True, order_by="Menu.sequence")