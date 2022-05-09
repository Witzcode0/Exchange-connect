"""
Models for "countries" package.
"""

from sqlalchemy.dialects.postgresql import JSONB

from app import db
from app.base.models import BaseModel


class UserActivityLog(BaseModel):

    __tablename__ = 'user_activity_log'

    login_log_id = db.Column(db.BigInteger, db.ForeignKey(
        'login_log.id', name='user_activity_log_login_log_id_fkey',
        ondelete='CASCADE'))
    user_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='user_activity_log_user_id_fkey', ondelete='CASCADE'),
                        nullable=False)
    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='user_activity_log_account_id_fkey',
        ondelete='CASCADE'), nullable=False)

    end_point = db.Column(db.String(128))
    method = db.Column(db.String(8))
    args = db.Column(JSONB)
    data = db.Column(JSONB)
    response_code = db.Column(db.Integer)
    front_end_url = db.Column(db.String(256))

    # relationships
    user = db.relationship('User', backref=db.backref(
        'user_activity_logs', lazy='dynamic'),
        foreign_keys='UserActivityLog.user_id')
    account = db.relationship('Account', backref=db.backref(
        'user_activity_logs', lazy='dynamic'),
        foreign_keys='UserActivityLog.account_id')
    login_log = db.relationship('LoginLog', backref=db.backref(
        'user_activity_logs', lazy='dynamic'),
        foreign_keys='UserActivityLog.login_log_id')

    def __init__(self, *args, **kwargs):
        super(UserActivityLog, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<LoginLog {} user {}>'.format(self.row_id, self.user_id)
