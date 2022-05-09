"""
Models for "corporate access event hosts" package.
"""

from sqlalchemy import UniqueConstraint, CheckConstraint

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString,ChoiceString
from app.base import constants as APP
# related model imports done in corporate_access_resources/__init__


class CorporateAccessEventHost(BaseModel):

    __tablename__ = 'corporate_access_event_host'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_host_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_host_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)

    corporate_access_event_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_access_event.id',
        name='corporate_access_event_host_corporate_access_event_id_fkey',
        ondelete='CASCADE'), nullable=False)
    host_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_host_host_id_fkey',
        ondelete='CASCADE'))

    host_email = db.Column(LCString(128))
    # if email is provided, then first_name and last_name is expected
    # (not required)
    host_first_name = db.Column(db.String(128))
    host_last_name = db.Column(db.String(128))
    host_designation = db.Column(db.String(128))

    # for mail sent or not
    is_mail_sent = db.Column(db.Boolean, default=False)
    email_status = db.Column(ChoiceString(APP.EMAIL_STATUS_CHOICES),
                             nullable=False, default=APP.EMAIL_NOT_SENT)

    # relationships
    corporate_access_event = db.relationship(
        'CorporateAccessEvent', backref=db.backref(
            'corporate_access_event_hosts', passive_deletes=True))
    corporate_external_event = db.relationship(
        'CorporateAccessEvent', backref=db.backref(
            'external_hosts', lazy='dynamic',
            passive_deletes=True))
    creator = db.relationship('User', backref=db.backref(
        'corporate_access_event_hosts_created', lazy='dynamic'),
        foreign_keys='CorporateAccessEventHost.created_by')
    host = db.relationship('User', backref=db.backref(
        'corporate_access_events_hosted', lazy='dynamic'),
        foreign_keys='CorporateAccessEventHost.host_id')
    host_j = db.relationship(
        'CorporateAccessEvent', secondary='user',
        backref=db.backref('hosted', uselist=False),
        foreign_keys='[CorporateAccessEventHost.corporate_access_event_id, '
                     'CorporateAccessEventHost.host_id, '
                     'CorporateAccessEventHost.host_email]',
        primaryjoin='CorporateAccessEvent.row_id == '
                    'CorporateAccessEventHost.corporate_access_event_id',
        secondaryjoin='or_(CorporateAccessEventHost.host_id == '
                      'User.row_id, '
                      'CorporateAccessEventHost.host_email == '
                      'User.email)',
        viewonly=True)

    # multi column
    __table_args__ = (
        CheckConstraint('((host_id IS NOT NULL) OR '
                        '(host_email IS NOT NULL))',
                        name='c_check_caei_host_id_host_email_'
                             'not_all_null_key'),
        UniqueConstraint('corporate_access_event_id', 'host_id',
                         name='c_corporate_access_event_id_host_id_key'),
        UniqueConstraint('corporate_access_event_id', 'host_email',
                         name='c_corporate_access_event_id_host_email_key')
    )

    def __init__(self, created_by=None, updated_by=None,
                 corporate_access_event_id=None, host_id=None,
                 *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        self.corporate_access_event_id = corporate_access_event_id
        self.host_id = host_id

        super(CorporateAccessEventHost, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CorporateAccessEventHost %r>' % (self.row_id)
