"""
Models for "Emeeting invitees" package.
"""

from sqlalchemy import CheckConstraint, UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString, ChoiceString
from app.base import constants as APP
# related model imports done in e_meeting/__init__


class EmeetingInvitee(BaseModel):

    __tablename__ = 'e_meeting_invitee'

    created_by = db.Column(db.BigInteger,
                           db.ForeignKey(
                               'user.id',
                               name='e_meeting_invitee_created_by_fkey',
                               ondelete='CASCADE'),
                           nullable=False)

    updated_by = db.Column(db.BigInteger,
                           db.ForeignKey(
                               'user.id',
                               name='e_meeting_invitee_updated_by_fkey',
                               ondelete='CASCADE'),
                           nullable=False)

    e_meeting_id = db.Column(db.BigInteger,
                             db.ForeignKey(
                                 'e_meeting.id',
                                 name='e_meeting_invitee_e_meeting_id_fkey',
                                 ondelete='CASCADE'),
                             nullable=False)

    invitee_id = db.Column(db.BigInteger,
                           db.ForeignKey(
                               'user.id',
                               name='e_meeting_invitee_invitee_id_fkey',
                               ondelete='CASCADE'))

    invitee_email = db.Column(LCString(128))
    # if email is provided, then first_name and last_name is expected

    conference_url = db.Column(db.String(256))

    # email field
    is_mail_sent = db.Column(db.Boolean, default=False)
    email_status = db.Column(ChoiceString(APP.EMAIL_STATUS_CHOICES),
                             nullable=False, default=APP.EMAIL_NOT_SENT)

    # relationships
    e_meeting = db.relationship(
        'Emeeting', backref=db.backref(
            'e_meeting_invitees', passive_deletes=True))

    invitee = db.relationship(
        'User', backref=db.backref(
            'e_meeting_invited', lazy='dynamic'),
        foreign_keys='EmeetingInvitee.invitee_id')

    invitee_j = db.relationship(
        'Emeeting', secondary='user', backref=db.backref('invited',
                                                         uselist=False),
        foreign_keys='['
        'EmeetingInvitee.e_meeting_id,EmeetingInvitee.invitee_id, '
        'EmeetingInvitee.invitee_email]',
        primaryjoin='Emeeting.row_id == EmeetingInvitee.e_meeting_id',
        secondaryjoin='or_(EmeetingInvitee.invitee_id == User.row_id)',
        viewonly=True)

    def __init__(self, created_by=None, updated_by=None,
                 invitee_id=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        self.invitee_id = invitee_id
        super(EmeetingInvitee, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<EmeetingInvitee %r>' % (self.row_id)
