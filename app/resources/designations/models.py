"""
Models for "designations" package.
"""

from sqlalchemy import func, Index

from app import db
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString
from app.resources.designations import constants as DESIGNATION
from app.resources.accounts import constants as ACCOUNT


class Designation(BaseModel):

    __tablename__ = 'designation'

    name = db.Column(db.String(256), nullable=False)
    designation_level = db.Column(ChoiceString(
        DESIGNATION.DES_LEVEL_TYPES_CHOICES), nullable=False)
    sequence = db.Column(db.Integer)
    account_type = db.Column(ChoiceString(ACCOUNT.ACCT_TYPES_CHOICES),
                             nullable=False)

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='designation_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='designation_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)

    __table_args__ = (
        # unique lower case index, i.e case-insensitive unique constraint
        Index('ci_designation_unique_name_account_type', func.lower(name),
              account_type, unique=True),
    )

    # relationships
    creator = db.relationship('User', backref=db.backref(
        'designations', lazy='dynamic'), foreign_keys='Designation.created_by')

    def __init__(self, name=None, *args, **kwargs):
        self.name = name
        super(Designation, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Designation %r>' % (self.row_id)
