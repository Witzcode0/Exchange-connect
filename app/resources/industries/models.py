"""
Models for "industries" package.
"""

from sqlalchemy import func, Index

from app import db
from app.base.models import BaseModel
from app.resources.sectors.models import Sector
# ^required for relationship


class Industry(BaseModel):

    __tablename__ = 'industry'

    name = db.Column(db.String(256), nullable=False)
    sector_id = db.Column(db.BigInteger, db.ForeignKey(
        'sector.id', name='industry_sector_id_fkey', ondelete='CASCADE'),
        nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='industry_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='industry_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)

    __table_args__ = (
        # unique lower case index, i.e case-insensitive unique constraint
        Index('ci_industry_unique_name', func.lower(name), unique=True),
    )

    # relationships
    sector = db.relationship('Sector', backref=db.backref(
        'industries', lazy='dynamic'))
    creator = db.relationship('User', backref=db.backref(
        'industries', lazy='dynamic'), foreign_keys='Industry.created_by')

    def __init__(self, name=None, created_by=None,
                 updated_by=None, *args, **kwargs):
        self.name = name
        self.created_by = created_by
        self.updated_by = updated_by
        super(Industry, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Industry %r>' % (self.row_id)
