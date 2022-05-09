"""
Models for "corporate access open meeting invitees" package.
"""

from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString
from app.corporate_access_resources.corporate_access_event_invitees import \
    constants as CA_EVENT_INVITEE
# related model imports done in corporate_access_resources/__init__


class CAOpenMeetingInvitee(BaseModel):

    __tablename__ = 'ca_open_meeting_invitee'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='ca_open_meeting_invitee_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='ca_open_meeting_invitee_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)
    ca_open_meeting_id = db.Column(db.BigInteger, db.ForeignKey(
        'ca_open_meeting.id', name='ca_open_meeting_invitee'
        '_corporate_access_event_id_fkey', ondelete='CASCADE'), nullable=False)

    invitee_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='ca_open_meeting_invitee_invitee_id_fkey',
        ondelete='CASCADE'), nullable=False)
    # status for different event types
    status = db.Column(ChoiceString(CA_EVENT_INVITEE.EVT_INV_STATUS_CHOICES),
                       nullable=False, default=CA_EVENT_INVITEE.INVITED)

    # multi column
    __table_args__ = (
        UniqueConstraint(
            'created_by', 'ca_open_meeting_id', 'invitee_id',
            name='c_created_by_ca_open_meeting_id_invitee_id_key'),
    )

    # relationships
    ca_open_meeting = db.relationship(
        'CAOpenMeeting', backref=db.backref(
            'ca_open_meeting_invitees', lazy='dynamic',
            passive_deletes=True))
    invitee = db.relationship('User', backref=db.backref(
        'open_meeting_invited', lazy='dynamic'),
        foreign_keys='CAOpenMeetingInvitee.invitee_id')
    invitee_j = db.relationship(
        'CAOpenMeeting', secondary='user',
        backref=db.backref('invited', uselist=False),
        foreign_keys='[CAOpenMeetingInvitee.ca_open_meeting_id, '
                     'CAOpenMeetingInvitee.invitee_id]',
        primaryjoin='CAOpenMeeting.row_id == '
                    'CAOpenMeetingInvitee.ca_open_meeting_id',
        secondaryjoin='CAOpenMeetingInvitee.invitee_id == User.row_id',
        viewonly=True)

    def __init__(self, created_by=None, updated_by=None,
                 ca_open_meeting_id=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        self.ca_open_meeting_id = ca_open_meeting_id
        super(CAOpenMeetingInvitee, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CAOpenMeetingInvitee %r>' % (self.row_id)
