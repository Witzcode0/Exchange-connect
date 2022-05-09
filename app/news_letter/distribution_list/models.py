"""
Models for "distribution list of user" package.
"""

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString

# related model imports done in toolkit/__init__


class DistributionList(BaseModel):

    __tablename__ = 'distribution_list'

    email = db.Column(LCString(128), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100))
    contact_number = db.Column(db.String(50))
    designation = db.Column(db.String(100))
    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='distribution_account_id_fkey', ondelete='CASCADE'),
        nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='distribution_list_created_by_fkey'))
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='distribution_list_updated_by_fkey'))

    creator = db.relationship('User', backref=db.backref(
        'distribution_list_creator', lazy='dynamic'),
    foreign_keys='DistributionList.created_by')
    account = db.relationship('Account', backref=db.backref(
        'distribution_list_account', lazy='dynamic'),
    foreign_keys='DistributionList.account_id')
    unsubscriptions = db.relationship('Unsubscription',  backref=db.backref(
        'distribution_list', lazy='dynamic'), foreign_keys='DistributionList.email',
         primaryjoin="Unsubscription.email == DistributionList.email", viewonly=True)

    def __init__(self, *args, **kwargs):
        super(DistributionList, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<DistributionList %r>' % (self.row_id)
