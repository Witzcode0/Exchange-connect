"""
Models for "webinar invitees" package.
"""

from sqlalchemy import CheckConstraint, UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString, ChoiceString
from app.webinar_resources.webinar_invitees import constants as WEBINARINVITEE
from app.base import constants as APP
# related model imports done in webinars/__init__


class WebinarInvitee(BaseModel):

    __tablename__ = 'webinar_invitee'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webinar_invitee_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webinar_invitee_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)
    webinar_id = db.Column(db.BigInteger, db.ForeignKey(
        'webinar.id', name='webinar_invitee_webinar_id_fkey',
        ondelete='CASCADE'), nullable=False)

    invitee_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webinar_invitee_invitee_id_fkey', ondelete='CASCADE'))
    invitee_email = db.Column(LCString(128))
    # if email is provided, then first_name and last_name is expected
    # (not required)
    invitee_first_name = db.Column(db.String(128))
    invitee_last_name = db.Column(db.String(128))
    invitee_designation = db.Column(db.String(128))
    invitee_company = db.Column(db.String(256))

    is_mail_sent = db.Column(db.Boolean, default=False)
    email_status = db.Column(ChoiceString(APP.EMAIL_STATUS_CHOICES),
        nullable=False, default=APP.EMAIL_NOT_SENT)
    status = db.Column(ChoiceString(WEBINARINVITEE.WBNR_INV_STATUS_CHOICES),
                       nullable=False, default=WEBINARINVITEE.INVITED)

    conference_url = db.Column(db.String(256))

    # multi column
    __table_args__ = (
        CheckConstraint('((invitee_id IS NOT NULL) OR '
                        '(invitee_email IS NOT NULL))',
                        name='c_check_wbninv_invitee_id_invitee_email_'
                        'not_all_null_key'),
        UniqueConstraint('webinar_id', 'invitee_email',
                         name='c_webinar_id_invitee_email_key'),
        UniqueConstraint('webinar_id', 'invitee_id',
                         name='c_webinar_id_invitee_id_key'),
    )

    # relationships
    webinar = db.relationship('Webinar', backref=db.backref(
        'webinar_invitees', passive_deletes=True))
    invitee = db.relationship('User', backref=db.backref(
        'webinars_invited', lazy='dynamic'),
        foreign_keys='WebinarInvitee.invitee_id')
    external_invitee = db.relationship('Webinar', backref=db.backref(
        'external_invitees', lazy='dynamic', passive_deletes=True))
    invitee_j = db.relationship(
        'Webinar', secondary='user', backref=db.backref(
            'invited', uselist=False),
        foreign_keys='[WebinarInvitee.webinar_id, WebinarInvitee.invitee_id, '
                     'WebinarInvitee.invitee_email]',
        primaryjoin='Webinar.row_id == WebinarInvitee.webinar_id',
        secondaryjoin='or_(WebinarInvitee.invitee_id == User.row_id, '
                      'WebinarInvitee.invitee_email == User.email)',
        viewonly=True)

    crm_group = db.relationship('User', backref=db.backref(
        'webinars_grp_invited', lazy='dynamic'),
        foreign_keys='[WebinarInvitee.invitee_email, WebinarInvitee.invitee_id]',
        primaryjoin='or_(WebinarInvitee.invitee_email == User.email,\
            WebinarInvitee.invitee_id == User.row_id)')

    def __init__(self, created_by=None, updated_by=None,
                 invitee_id=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        self.invitee_id = invitee_id
        super(WebinarInvitee, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<WebinarInvitee %r>' % (self.row_id)
