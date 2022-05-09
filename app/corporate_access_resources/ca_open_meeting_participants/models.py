"""
Models for "corporate access open meeting participants" package.
"""

from sqlalchemy import CheckConstraint, UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString
# related model imports done in corporate_access_resources/__init__


class CAOpenMeetingParticipant(BaseModel):

    __tablename__ = 'ca_open_meeting_participant'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='ca_open_meeting_participant_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='ca_open_meeting_participant_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)

    ca_open_meeting_id = db.Column(db.BigInteger, db.ForeignKey(
        'ca_open_meeting.id', name='ca_open_meeting_id_fkey',
        ondelete='CASCADE'), nullable=False)
    participant_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='ca_open_meeting_participant_'
        'participant_id_fkey', ondelete='CASCADE'))
    participant_email = db.Column(LCString(128))
    # if email is provided, then first_name and last_name is expected
    # (not required)
    participant_first_name = db.Column(db.String(128))
    participant_last_name = db.Column(db.String(128))
    participant_designation = db.Column(db.String(128))

    sequence_id = db.Column(db.Integer)

    # relationships
    ca_open_meeting = db.relationship(
        'CAOpenMeeting', backref=db.backref(
            'ca_open_meeting_participants', passive_deletes=True))
    ca_open_meeting_participant = db.relationship(
        'CAOpenMeeting', backref=db.backref(
            'external_participants', lazy='dynamic',
            passive_deletes=True))
    creator = db.relationship('User', backref=db.backref(
        'ca_open_meeting_participants_created', lazy='dynamic'),
        foreign_keys='CAOpenMeetingParticipant.created_by')
    participant = db.relationship('User', backref=db.backref(
        'ca_open_meeting_participated', lazy='dynamic'),
        foreign_keys='CAOpenMeetingParticipant.participant_id')

    # multi column
    __table_args__ = (
        CheckConstraint('((participant_id IS NOT NULL) OR '
                        '(participant_email IS NOT NULL))',
                        name='c_check_caopem_participant_id_participant_email_'
                        'not_all_null_key'),
        UniqueConstraint(
            'ca_open_meeting_id', 'participant_email',
            name='c_caopen_evt_met_id_participant_email_key'),
        UniqueConstraint(
            'ca_open_meeting_id', 'participant_id',
            name='c_caopen_evt_met_id_participant_id_key'),
        UniqueConstraint(
            'ca_open_meeting_id', 'sequence_id',
            name='c_caopen_met_id_sequence_id_key')
    )

    def __init__(self, created_by=None, updated_by=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        super(CAOpenMeetingParticipant, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CAOpenMeetingParticipant %r>' % (self.row_id)
