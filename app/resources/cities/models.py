"""
Models for "cities" package.
"""

from sqlalchemy import func, Index

from app import db
from app.base.models import BaseModel


class City(BaseModel):

    __tablename__ = 'city'
    __global_searchable__ = ['city_name']

    city_name = db.Column(db.String(128), nullable=False)
    country_id = db.Column(db.BigInteger, db.ForeignKey(
        'country.id', name='city_country_id_fkey', ondelete='CASCADE'),
        nullable=False)
    state_id = db.Column(db.BigInteger, db.ForeignKey(
        'state.id', name='city_state_id_fkey', ondelete='CASCADE'),
        nullable=False)

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='city_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='city_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)

    deleted = db.Column(db.Boolean, default=False)

    __table_args__ = (
        Index('ci_country_id_state_id_city_name_key',
              country_id, state_id, func.lower(city_name), unique=True),
    )

    creator = db.relationship('User', backref=db.backref(
        'cities', lazy='dynamic'), foreign_keys='City.created_by')

    def __init__(self, city_name=None, created_by=None, updated_by=None,
                 country_id=None, state_id=None, *args, **kwargs):
        self.city_name = city_name
        self.created_by = created_by
        self.updated_by = updated_by
        self.country_id = country_id
        self.state_id = state_id
        super(City, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<City %r>' % (self.row_id)
