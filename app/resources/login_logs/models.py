"""
Models for "countries" package.
"""
import datetime

from sqlalchemy.dialects.postgresql import JSONB

from app import db
from app.base.models import BaseModel


class LoginLog(BaseModel):

    __tablename__ = 'login_log'

    login_time = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    logout_time = db.Column(db.DateTime)
    last_active_time = db.Column(db.DateTime)
    user_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='login_log_user_id_fkey', ondelete='CASCADE'),
                        nullable=False)
    domain_id = db.Column(db.BigInteger, db.ForeignKey(
        'domain.id', name='login_log_domain_id_fkey', ondelete='RESTRICT'),
                          nullable=False)
    ip = db.Column(db.String(16))
    browser = db.Column(db.String(32))
    platform = db.Column(db.String(32))
    browser_version = db.Column(db.String(64))
    device = db.Column(db.String(16))
    continent_code = db.Column(db.String(2))
    continent = db.Column(db.String(16))
    country_code = db.Column(db.String(2))
    country = db.Column(db.String(128))
    region_code = db.Column(db.String(16))
    region = db.Column(db.String(128))
    city = db.Column(db.String(128))
    postal_code = db.Column(db.String(16))
    location = db.Column(JSONB)

    # relationships
    user = db.relationship('User', backref=db.backref(
        'login_logs', lazy='dynamic'), foreign_keys='LoginLog.user_id')

    def __init__(self, *args, **kwargs):
        super(LoginLog, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<LoginLog {} user {}>'.format(self.row_id, self.user_id)
