"""
Models for "market analyst performance" package.
"""

from app import db
from app.base.models import BaseModel
# related model imports done in toolkit/__init__


class MarketPerformance(BaseModel):

    __tablename__ = 'market_performance'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='market_account_fkey'))
    account_sort_name = db.Column(db.String(100))
    account_id_null_boolean = db.Column(db.Boolean, default=False)
    open_price = db.Column(db.String(100))
    high_price = db.Column(db.String(100))
    low_price = db.Column(db.String(100))
    prev_close_price = db.Column(db.String(100))
    ltp_price = db.Column(db.String(100))
    chng_price = db.Column(db.String(100))
    h_price_52w = db.Column(db.String(100))
    l_price_52w = db.Column(db.String(100))
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='market_performance_created_by_fkey'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='market_performance_updated_by_fkey'), nullable=False)

    account = db.relationship('Account', backref=db.backref(
        'market_performance_account', lazy='dynamic'))
    creator = db.relationship('User', backref=db.backref(
        'market_performance_creator', lazy='dynamic'),
    foreign_keys='MarketPerformance.created_by')

    def __init__(self, *args, **kwargs):
        super(MarketPerformance, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<MarketPerformance %r>' % (self.row_id)
