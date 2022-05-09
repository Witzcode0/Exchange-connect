"""
Models for "permissions" package.
"""

from app import db
from app.base.models import BaseModel


class Permission(BaseModel):

    __tablename__ = 'permission'

    name = db.Column(db.String(256), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True)
    sequence = db.Column(db.Integer)
    description = db.Column(db.String(256))
    code = db.Column(db.String(32), nullable=False, unique=True)

    def __init__(self, *args, **kwargs):
        super(Permission, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Permission row_id=%r, name=%r>' % (
            self.row_id, self.name)

