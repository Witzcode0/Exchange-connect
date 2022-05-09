"""
Models for "Result tracker companies" package.
"""
from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.resources.result_tracker.models import ResultTrackerGroup


class ResultTrackerGroupCompanies(BaseModel):

    __tablename__ = 'result_tracker_group_companies'

    group_id = db.Column(db.BigInteger, db.ForeignKey(
        'result_tracker_group.id', name='result_tracker_user_company_fkey', ondelete='CASCADE'))

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='result_tracker_account_id_fkey', ondelete='CASCADE'),
        nullable=False)
    user_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='result_tracker_group_company_user_fkey', ondelete='CASCADE'))
    # manage sequence of the groups companies
    sequence_id = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint('group_id', 'account_id', 'user_id',
                         name='result_tracker_group_id_account_id_user_id_uniquekey'),
    )

    # relationships
    account = db.relationship('Account', backref=db.backref(
        'account_id', lazy='dynamic'))

    group = db.relationship('ResultTrackerGroup', backref=db.backref(
        'group_id', lazy='dynamic'))
