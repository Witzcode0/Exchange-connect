"""
Models for "market analyst comment" package.
"""

from app import db
from app.base.models import BaseModel
# related model imports done in toolkit/__init__


class MarketAnalystComment(BaseModel):

    __tablename__ = 'market_analyst_comment'

    comment = db.Column(db.String())
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='market_account_created_by_fkey'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='market_account_updated_by_fkey'), nullable=False)
    domain_id = db.Column(db.BigInteger, db.ForeignKey(
        'domain.id', name='market_comment_domain_id_fkey'), nullable=False)
    subject = db.Column(db.String())

    creator = db.relationship('User', backref=db.backref(
        'market_analyst_comment_creator', lazy='dynamic'),
    foreign_keys='MarketAnalystComment.created_by')
    domain = db.relationship('Domain', backref=db.backref(
        'market_analyst_comment_domain', lazy='dynamic'),
    foreign_keys='MarketAnalystComment.domain_id')

    def __init__(self, *args, **kwargs):
        super(MarketAnalystComment, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<MarketAnalystComment %r>' % (self.row_id)
