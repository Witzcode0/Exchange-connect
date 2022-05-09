"""
models for result master
"""
from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.resources.bse.models import BSEFeed


class AccountResultTracker(BaseModel):
    __tablename__ = 'account_result_tracker'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='result_master_account_id_fkey', ondelete='CASCADE'),
                           nullable=False)
    concall_date = db.Column(db.DateTime)
    concall_bse_id = db.Column(db.BigInteger, db.ForeignKey(
        'bse_corp_feed.id', name='account_result_tracker_concall_bse_id_fkey', ondelete='CASCADE'),
              nullable=True)
    result_intimation_id = db.Column(db.BigInteger, db.ForeignKey(
        'bse_corp_feed.id', name='account_result_tracker_result_intimation_id_fkey', ondelete='CASCADE'),
              nullable=True)
    result_declaration_id = db.Column(db.BigInteger, db.ForeignKey(
        'bse_corp_feed.id', name='account_result_tracker_result_declaration_id_fkey', ondelete='CASCADE'),
              nullable=True)

    __table_args__ = (
        UniqueConstraint('account_id',
                         name='result_tracker_account_id_key'),
    )

    # relationships
    account = db.relationship('Account', backref=db.backref(
        'result_account', lazy='dynamic'))
    concall_bse_feed = db.relationship('BSEFeed', backref=db.backref(
        'result_concall_bse_feed', lazy='dynamic'), foreign_keys='AccountResultTracker.concall_bse_id')
    result_intimation_feed = db.relationship('BSEFeed', backref=db.backref(
        'result_intimation_feed', lazy='dynamic'), foreign_keys='AccountResultTracker.result_intimation_id')
    result_declaration_feed = db.relationship('BSEFeed', backref=db.backref(
        'result_declaration_feed', lazy='dynamic'), foreign_keys='AccountResultTracker.result_declaration_id')
