"""
Models for "webcast invitees" package.
"""

from sqlalchemy import CheckConstraint, UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString, ChoiceString
from app.webcast_resources.webcast_invitees import constants as WEBCASTINVITEE
from app.base import constants as APP
# related model imports done in webcasts/__init__


class WebcastInvitee(BaseModel):

    __tablename__ = 'webcast_invitee'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webcast_invitee_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webcast_invitee_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)
    webcast_id = db.Column(db.BigInteger, db.ForeignKey(
        'webcast.id', name='webcast_invitee_webcast_id_fkey',
        ondelete='CASCADE'), nullable=False)

    invitee_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webcast_invitee_invitee_id_fkey', ondelete='CASCADE'))
    invitee_email = db.Column(LCString(128))
    is_mail_sent = db.Column(db.Boolean, default=False)
    email_status = db.Column(ChoiceString(APP.EMAIL_STATUS_CHOICES),
                             nullable=False, default=APP.EMAIL_NOT_SENT)
    # if email is provided, then first_name, last_name and designation
    # is expected (not required)
    invitee_first_name = db.Column(db.String(128))
    invitee_last_name = db.Column(db.String(128))
    invitee_designation = db.Column(db.String(128))

    status = db.Column(ChoiceString(WEBCASTINVITEE.WBCT_INV_STATUS_CHOICES),
                       nullable=False, default=WEBCASTINVITEE.INVITED)

    conference_url = db.Column(db.String(256))

    # the actual final user, i.e after creating guest account, or copy of
    # user_id, for already existing system users who directly join, or users
    # from contacts
    user_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webcast_invitee_user_id_fkey', ondelete='CASCADE'))

    # multi column
    __table_args__ = (
        CheckConstraint('((invitee_id IS NOT NULL) OR '
                        '(invitee_email IS NOT NULL))',
                        name='c_check_wbcinv_invitee_id_invitee_email_'
                        'not_all_null_key'),
        UniqueConstraint('webcast_id', 'invitee_email',
                         name='c_webcast_id_invitee_email_key'),
        UniqueConstraint('webcast_id', 'invitee_id',
                         name='c_webcast_id_invitee_id_key'),
    )

    # relationships
    webcast = db.relationship('Webcast', backref=db.backref(
        'webcast_invitees', lazy='dynamic', passive_deletes=True))
    invitee = db.relationship('User', backref=db.backref(
        'webcasts_invited', lazy='dynamic'),
        foreign_keys='WebcastInvitee.invitee_id')
    crm_group = db.relationship('User', backref=db.backref(
        'webcast_crm_group', lazy='dynamic'),
        foreign_keys='WebcastInvitee.user_id')
    webcast_external_invitee = db.relationship('Webcast', backref=db.backref(
        'external_invitees', lazy='dynamic', passive_deletes=True))
    invitee_j = db.relationship(
        'Webcast', secondary='user',
        backref=db.backref('invited', uselist=False),
        foreign_keys='[WebcastInvitee.webcast_id, WebcastInvitee.invitee_id, '
                     'WebcastInvitee.invitee_email]',
        primaryjoin='Webcast.row_id == WebcastInvitee.webcast_id',
        secondaryjoin='or_(WebcastInvitee.invitee_id == User.row_id, '
                      'WebcastInvitee.invitee_email == User.email)',
        viewonly=True)

    def __init__(self, created_by=None, updated_by=None,
                 invitee_id=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        self.invitee_id = invitee_id
        super(WebcastInvitee, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<WebcastInvitee %r>' % (self.row_id)
