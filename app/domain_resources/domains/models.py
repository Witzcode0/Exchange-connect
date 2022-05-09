"""
Models for "domains" package.
"""

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString


class Domain(BaseModel):

    __tablename__ = 'domain'

    name = db.Column(LCString(512), nullable=False, unique=True)
    country = db.Column(db.String(128))
    is_active = db.Column(db.Boolean, default=False)
    code = db.Column(db.String(8), nullable=False, unique=True)
    currency = db.Column(db.String(32))
    google_address_code = db.Column(db.String(32))
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='domain_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='domain_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)

    def __init__(self, name=None, country=None, created_by=None, updated_by=None,
                 *args, **kwargs):
        self.name = name
        self.country = country
        self.created_by = created_by
        self.updated_by = updated_by
        super(Domain, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Domain {}>'.format(self.row_id)
