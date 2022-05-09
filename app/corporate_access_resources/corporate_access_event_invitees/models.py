"""
Models for "corporate access event invitees" package.
"""

from sqlalchemy import CheckConstraint, UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString, ChoiceString
from app.base import constants as APP
from app.corporate_access_resources.corporate_access_event_invitees import \
    constants as CA_EVENT_INVITEE
# related model imports done in corporate_access_resources/__init__


class CorporateAccessEventInvitee(BaseModel):

    __tablename__ = 'corporate_access_event_invitee'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_invitee_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_invitee_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)
    corporate_access_event_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_access_event.id', name='corporate_access_event_invitee'
        '_corporate_access_event_id_fkey', ondelete='CASCADE'), nullable=False)

    # can't set null ondelete here, as either id, or email is required
    invitee_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_invitee_invitee_id_fkey',
        ondelete='CASCADE'))
    invitee_email = db.Column(LCString(128))
    # if email is provided, then first_name and last_name is expected
    # (not required)
    invitee_first_name = db.Column(db.String(128))
    invitee_last_name = db.Column(db.String(128))
    invitee_designation = db.Column(db.String(128))
    invitee_company = db.Column(db.String(128))

    # the actual final user, i.e after creating guest account, or copy of
    # user_id, for already existing system users who directly join, or users
    # from contacts
    user_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_invitee_user_id_fkey',
        ondelete='CASCADE'))

    # status for different event types
    status = db.Column(ChoiceString(CA_EVENT_INVITEE.EVT_INV_STATUS_CHOICES),
                       nullable=False, default=CA_EVENT_INVITEE.INVITED)
    # for one-to-one meeting, invitee can put remark
    invitee_remark = db.Column(db.String(2048))
    # for open to all event
    uninvited = db.Column(db.Boolean, default=False)
    # for mail sent or not
    is_mail_sent = db.Column(db.Boolean, default=False)
    email_status = db.Column(ChoiceString(APP.EMAIL_STATUS_CHOICES),
                             nullable=False, default=APP.EMAIL_NOT_SENT)

    # multi column
    __table_args__ = (
        CheckConstraint('((invitee_id IS NOT NULL) OR '
                        '(invitee_email IS NOT NULL))',
                        name='c_check_caei_invitee_id_invitee_email_'
                        'not_all_null_key'),
        UniqueConstraint(
            'created_by', 'corporate_access_event_id', 'invitee_email',
            name='c_created_by_corpacc_event_id_invitee_email_key'),
        UniqueConstraint(
            'created_by', 'corporate_access_event_id', 'invitee_id',
            name='c_created_by_corpacc_event_id_invitee_id_key'),
    )

    # relationships
    corporate_access_event = db.relationship(
        'CorporateAccessEvent', backref=db.backref(
            'corporate_access_event_invitees', lazy='dynamic',
            passive_deletes=True))
    invitee = db.relationship('User', backref=db.backref(
        'corporate_access_events_invited', lazy='dynamic'),
        foreign_keys='CorporateAccessEventInvitee.invitee_id')
    crm_group = db.relationship('User', backref=db.backref(
        'corporate_access_events_crm_group', lazy='dynamic'),
        foreign_keys='CorporateAccessEventInvitee.user_id')
    external_invitee_event = db.relationship(
        'CorporateAccessEvent', backref=db.backref(
            'external_invitees', lazy='dynamic',
            passive_deletes=True))
    invitee_j = db.relationship(
        'CorporateAccessEvent', secondary='user',
        backref=db.backref('invited', uselist=False),
        foreign_keys='[CorporateAccessEventInvitee.corporate_access_event_id, '
                     'CorporateAccessEventInvitee.invitee_id, '
                     'CorporateAccessEventInvitee.invitee_email]',
        primaryjoin='CorporateAccessEvent.row_id == '
                    'CorporateAccessEventInvitee.corporate_access_event_id',
        secondaryjoin='or_(CorporateAccessEventInvitee.invitee_id == '
                      'User.row_id, '
                      'CorporateAccessEventInvitee.invitee_email == '
                      'User.email)',
        viewonly=True)

    def __init__(self, created_by=None, updated_by=None,
                 corporate_access_event_id=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        self.corporate_access_event_id = corporate_access_event_id
        super(CorporateAccessEventInvitee, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CorporateAccessEventInvitee %r>' % (self.row_id)
