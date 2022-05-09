"""
Models for "account user members" package.
"""

from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel


class AccountUserMember(BaseModel):

    __tablename__ = 'account_user_member'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='account_user_member_account_id_fkey',
        ondelete='CASCADE'), nullable=False)
    member_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='account_user_member_member_id_fkey',
        ondelete='CASCADE'), nullable=False)
    member_is_admin = db.Column(db.Boolean, default=False)

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='account_user_member_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='account_user_member_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)

    __table_args__ = (
        UniqueConstraint('account_id', 'member_id',
                         name='c_aum_account_id_member_id_key'),
    )

    # relationships
    member = db.relationship('User', backref=db.backref(
        'account_user_member', lazy='dynamic'),
        foreign_keys='AccountUserMember.member_id')
    creator = db.relationship('User', backref=db.backref(
        'account_user_member_creator', lazy='dynamic'),
        foreign_keys='AccountUserMember.created_by')
    account = db.relationship('Account', backref=db.backref(
        'account_user_member', uselist=False),
        foreign_keys='AccountUserMember.account_id')
    member_j = db.relationship(
        'User', secondary='account',
        backref=db.backref('membership', uselist=False),
        foreign_keys='[AccountUserMember.account_id, '
                     'AccountUserMember.member_id]',
        primaryjoin='User.row_id == AccountUserMember.member_id',
        secondaryjoin='AccountUserMember.account_id == Account.row_id',
        viewonly=True)

    def __init__(self, created_by=None, updated_by=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        super(AccountUserMember, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<AccountUserMember %r>' % (self.row_id)

# #TODO: add a history table?
