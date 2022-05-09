"""
Models for "event invites" package.
"""

from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString
from app.resources.event_invites import constants as EVENT_INVITE
from app.resources.events.models import Event


class EventInvite(BaseModel):

    __tablename__ = 'event_invite'

    status = db.Column(ChoiceString(EVENT_INVITE.EVT_INV_STATUS_CHOICES),
                       nullable=False, default=EVENT_INVITE.INVITED)

    rating = db.Column(db.Integer)

    event_id = db.Column(db.BigInteger, db.ForeignKey(
        'event.id', name='event_invite_event_id_fkey', ondelete='CASCADE'),
        nullable=False)
    user_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='event_invite_user_id_fkey', ondelete='CASCADE'),
        nullable=False)

    comment = db.Column(db.String(1024))
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='event_invite_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='event_invite_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)
    deleted = db.Column(db.Boolean, default=False)

    # relationships
    event = db.relationship('Event', backref=db.backref('invites'))
    invitee = db.relationship('User', backref=db.backref(
        'event_invites', lazy='dynamic'), foreign_keys='EventInvite.user_id')

    # multi column
    __table_args__ = (
        UniqueConstraint('event_id', 'user_id',
                         name='c_event_id_user_id_key'),
    )

    def __init__(self, event_id=None, status=None, user_id=None,
                 *args, **kwargs):
        self.event_id = event_id
        self.user_id = user_id
        self.status = status
        super(EventInvite, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<EventInvite %r>' % (self.row_id)
