"""
Models for "follows" package.
"""

from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.resources.account_profiles.models import AccountProfile
from app.resources.users.models import User


class CFollow(BaseModel):
    """
    Tracks company (account) follows
    """

    __tablename__ = 'c_follow'

    sent_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='c_follow_sent_by_fkey', ondelete='CASCADE'),
        nullable=False)
    company_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='c_follow_company_id_fkey', ondelete='CASCADE'),
        nullable=False)

    follower = db.relationship('User', backref=db.backref(
        'following', lazy='dynamic'))
    company = db.relationship('Account', backref=db.backref(
        'followers', lazy='dynamic'))
    # special relationship for already followed eager loading check
    company_j = db.relationship('AccountProfile', backref=db.backref(
        'followed', uselist=False),
        foreign_keys='CFollow.company_id',
        primaryjoin='AccountProfile.account_id == CFollow.company_id')

    # multi column
    __table_args__ = (
        UniqueConstraint('sent_by', 'company_id',
                         name='c_sent_by_company_id_key'),
    )

    def __init__(self, sent_by=None, company_id=None, *args, **kwargs):
        self.sent_by = sent_by
        self.company_id = company_id
        super(CFollow, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CFollow %r>' % (self.sent_by)


class CFollowHistory(BaseModel):
    """
    Maintains a follow history, incase of deletions.
    """

    __tablename__ = 'follow_history'

    sent_by = db.Column(db.BigInteger, nullable=False)
    company_id = db.Column(db.BigInteger, nullable=False)

    def __init__(self, sent_by=None, company_id=None, *args, **kwargs):
        self.sent_by = sent_by
        self.company_id = company_id
        super(CFollowHistory, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CFollowHistory %r>' % (self.sent_by)
