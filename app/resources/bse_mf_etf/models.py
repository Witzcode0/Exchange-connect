"""
Models for "bse etf and mututal fund" package.
"""
from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel

class BSEMFETFFeed(BaseModel):
    __tablename__ = 'bse_mf_etf_feed'

    scrip_cd = db.Column(db.String)
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
    trade_date = db.Column(db.DateTime)

    def __init__(self, *args, **kwargs):
        super(BSEMFETFFeed, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<BSEMFETFFeed %r>' % (self.row_id)