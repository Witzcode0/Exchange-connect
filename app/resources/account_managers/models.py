"""
Models for "account managers" package.
"""

from app import db
from app.base.models import BaseModel


class AccountManager(BaseModel):

    __tablename__ = 'account_manager'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='account_manager_account_id_fkey',
        ondelete='CASCADE'), unique=True, nullable=False)
    manager_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='account_manager_manager_id_fkey',
        ondelete='CASCADE'), nullable=False)

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='account_manager_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='account_manager_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)

    # relationships
    manager = db.relationship('User', backref=db.backref(
        'account_manager', lazy='dynamic'),
        foreign_keys='AccountManager.manager_id')
    creator = db.relationship('User', backref=db.backref(
        'account_manager_creator', lazy='dynamic'),
        foreign_keys='AccountManager.created_by')
    account = db.relationship('Account', backref=db.backref(
        'account_manager', uselist=False),
        foreign_keys='AccountManager.account_id')

    def __init__(self, created_by=None, updated_by=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        super(AccountManager, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<AccountManager %r>' % (self.row_id)


class AccountManagerHistory(BaseModel):

    __tablename__ = 'account_manager_history'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='account_manager_history_account_id_fkey',
        ondelete='CASCADE'), nullable=False)
    manager_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='account_manager_history_manager_id_fkey',
        ondelete='CASCADE'), nullable=False)

    # relationships
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='account_manager_history_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='account_manager_history_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)

    def __init__(self, created_by=None, updated_by=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        super(AccountManagerHistory, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<AccountManagerHistory %r>' % (self.row_id)
