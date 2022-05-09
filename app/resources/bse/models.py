"""
Models for "feeds" package.
"""
from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.resources.corporate_announcements_category.models import CorporateAnnouncementCategory


bsefeedaccounts = db.Table(
    'bsefeedaccounts',
    db.Column('feed_id', db.BigInteger, db.ForeignKey(
        'bse_corp_feed.id', name='bsefeedaccounts_feed_id_fkey', ondelete="CASCADE"),
        nullable=False),
    db.Column('account_id', db.Integer, db.ForeignKey(
        'account.id', name='bsefeedaccounts_account_id_fkey',
        ondelete="CASCADE"), nullable=False),
    UniqueConstraint('feed_id', 'account_id', name='ac_feed_id_account_id_key'),
)


class BSEFeed(BaseModel):

    __tablename__ = 'bse_corp_feed'

    scrip_cd = db.Column(db.String)
    acc_id = db.Column(db.Integer, db.ForeignKey('account.id'),
                           nullable=True)
    company_name = db.Column(db.String)
    dt_tm = db.Column(db.DateTime)
    file_status = db.Column(db.String)
    head_line = db.Column(db.String)
    news_sub = db.Column(db.String)
    attachment_name = db.Column(db.String)
    news_body = db.Column(db.String)
    descriptor = db.Column(db.String)
    critical_news = db.Column(db.String)
    type_of_announce = db.Column(db.String)
    type_of_meeting = db.Column(db.String)
    date_of_meeting = db.Column(db.DateTime)
    descriptor_id = db.Column(db.BigInteger)
    attachment_url = db.Column(db.String)
    exchange_category = db.Column(db.String)
    ec_category = db.Column(db.Integer, db.ForeignKey('corporate_announcement_category.id'))
    deleted = db.Column(db.Boolean, default=False)
    source = db.Column(db.String, default='bse_api')
    trade_date = db.Column(db.DateTime)
    is_mfetf = db.Column(db.Boolean, default=False)

    # relationships
    account = db.relationship('Account', backref=db.backref(
        'acc_id', lazy='dynamic'))
    category = db.relationship('CorporateAnnouncementCategory',
                               uselist=False,
                backref=db.backref('ec_category', lazy='dynamic'))

    bsefeedaccount = db.relationship(
        'Account', secondary=bsefeedaccounts, backref=db.backref(
            'bse_corp_feeds', lazy='dynamic'), passive_deletes=True)

    def __init__(self, *args, **kwargs):
        super(BSEFeed, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<BSEFeed %r>' % (self.row_id)


# class BSE_Descriptor(BaseModel):
#     __tablename__ = 'descriptor_master'
#
#     descriptor_id = db.Column(db.Integer)
#     descriptor_name = db.Column(db.String)
#     category_id = db.Column(db.Integer, db.ForeignKey('corporate_announcement_category.id'))