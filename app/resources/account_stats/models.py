"""
Models for "account stats" package.
"""

from app import db
from app.base.models import BaseModel


class AccountStats(BaseModel):

    __tablename__ = 'account_stats'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='account_stats_account_id_fkey',
        ondelete='CASCADE'), nullable=False)

    total_users = db.Column(db.BigInteger, default=0)

    # relationships
    account = db.relationship('Account', backref=db.backref(
        'stats', uselist=False, passive_deletes=True),
        primaryjoin='Account.row_id == AccountStats.account_id')

    def __init__(self, account_id=None, *args, **kwargs):
        self.account_id = account_id
        super(AccountStats, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<AccountStats %r>' % (self.account_id)
