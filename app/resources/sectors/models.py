"""
Models for "sectors" package.
"""

from sqlalchemy import func, Index

from app import db
from app.base.models import BaseModel


class Sector(BaseModel):

    __tablename__ = 'sector'

    name = db.Column(db.String(256), nullable=False)

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='sector_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='sector_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)

    __table_args__ = (
        # unique lower case index, i.e case-insensitive unique constraint
        Index('ci_sector_unique_name', func.lower(name), unique=True),
    )

    # relationships
    creator = db.relationship('User', backref=db.backref(
        'sectors', lazy='dynamic'), foreign_keys='Sector.created_by')

    def __init__(self, name=None, created_by=None, updated_by=None,
                 *args, **kwargs):
        self.name = name
        self.created_by = created_by
        self.updated_by = updated_by
        super(Sector, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Sector %r>' % (self.row_id)
