"""
Models for "countries" package.
"""

from sqlalchemy import Index, func

from app import db
from app.base.models import BaseModel


class Country(BaseModel):

    __tablename__ = 'country'

    country_name = db.Column(db.String(128), nullable=False)
    # ^unique case-insensitive below
    country_code = db.Column(db.String(2))  # unique case-insensitive below

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='country_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='country_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)

    deleted = db.Column(db.Boolean, default=False)

    __table_args__ = (
        # unique lower case index, i.e case-insensitive unique constraint
        Index('ci_country_unique_name', func.lower(country_name), unique=True),
        Index('ci_country_unique_code', func.lower(country_code), unique=True),
    )

    creator = db.relationship('User', backref=db.backref(
        'countries', lazy='dynamic'), foreign_keys='Country.created_by')

    def __init__(self, country_name=None, created_by=None, updated_by=None,
                 *args, **kwargs):
        self.country_name = country_name
        self.created_by = created_by
        self.updated_by = updated_by
        super(Country, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Country %r>' % (self.row_id)
