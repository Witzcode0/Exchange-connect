"""
Models for "webcast hosts" package.
"""

from sqlalchemy import UniqueConstraint, CheckConstraint

from app import db
from app.base.model_fields import LCString, ChoiceString
from app.base.models import BaseModel
from app.base import constants as APP
# related model imports done in webcasts/__init__


class WebcastHost(BaseModel):

    __tablename__ = 'webcast_host'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webcast_host_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webcast_host_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)

    webcast_id = db.Column(db.BigInteger, db.ForeignKey(
        'webcast.id', name='webcast_host_webcast_id_fkey',
        ondelete='CASCADE'), nullable=False)
    host_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webcast_host_host_id_fkey', ondelete='CASCADE'))

    host_email = db.Column(LCString(128))
    is_mail_sent = db.Column(db.Boolean, default=False)
    email_status = db.Column(ChoiceString(APP.EMAIL_STATUS_CHOICES),
                             nullable=False, default=APP.EMAIL_NOT_SENT)
    # if email is provided, then first_name and last_name is expected
    # (not required)
    host_first_name = db.Column(db.String(128))
    host_last_name = db.Column(db.String(128))
    host_designation = db.Column(db.String(128))

    # url for bigmarker conference
    conference_url = db.Column(db.String(256))

    # multi column
    __table_args__ = (
        CheckConstraint('((host_id IS NOT NULL) OR '
                        '(host_email IS NOT NULL))',
                        name='c_check_wbch_host_id_host_email_'
                        'not_all_null_key'),
        UniqueConstraint('webcast_id', 'host_email',
                         name='c_webcast_id_host_email_key'),
        UniqueConstraint('webcast_id', 'host_id',
                         name='c_webcast_id_host_id_key'),
    )

    # relationships
    webcast = db.relationship('Webcast', backref=db.backref(
        'webcast_hosts', lazy='dynamic', passive_deletes=True))
    creator = db.relationship('User', backref=db.backref(
        'webcast_hosts_created', lazy='dynamic'),
        foreign_keys='WebcastHost.created_by')
    host = db.relationship('User', backref=db.backref(
        'webcasts_hosted', lazy='dynamic'),
        foreign_keys='WebcastHost.host_id')
    webcast_external_host = db.relationship('Webcast', backref=db.backref(
        'external_hosts', lazy='dynamic', passive_deletes=True))

    def __init__(self, created_by=None, updated_by=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        super(WebcastHost, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<WebcastHost %r>' % (self.row_id)
