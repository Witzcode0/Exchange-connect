"""
Models for "states" package.
"""

from sqlalchemy import func, Index

from app import db
from app.base.models import BaseModel


class State(BaseModel):

    __tablename__ = 'state'

    state_name = db.Column(db.String(128), nullable=False)
    state_code = db.Column(db.String(16))  # unique case-insensitive below
    country_id = db.Column(db.BigInteger, db.ForeignKey(
        'country.id', name='state_country_id_fkey', ondelete='CASCADE'),
        nullable=False)

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='state_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='state_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)

    deleted = db.Column(db.Boolean, default=False)

    __table_args__ = (
        Index('ci_state_country_id_state_name_key',
              country_id, func.lower(state_name), unique=True),
        Index('ci_state_state_code_key', func.lower(state_code), unique=True),
    )

    creator = db.relationship('User', backref=db.backref(
        'states', lazy='dynamic'), foreign_keys='State.created_by')

    def __init__(self, state_name=None, created_by=None, updated_by=None,
                 country_id=None, *args, **kwargs):
        self.state_name = state_name
        self.created_by = created_by
        self.updated_by = updated_by
        self.country_id = country_id
        super(State, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<State %r>' % (self.row_id)
