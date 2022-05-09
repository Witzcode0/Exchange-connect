"""
Models for "corporate access event participants" package.
"""

from sqlalchemy import CheckConstraint, UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString, ChoiceString
from app.base import constants as APP
# related model imports done in corporate_access_resources/__init__


class CorporateAccessEventParticipant(BaseModel):

    __tablename__ = 'corporate_access_event_participant'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_participant_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_participant_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)

    corporate_access_event_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_access_event.id',
        name='cracs_event_participant_corporate_access_event_id_fkey',
        ondelete='CASCADE'), nullable=False)
    participant_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_participant_'
        'participant_id_fkey', ondelete='CASCADE'))
    participant_email = db.Column(LCString(128))
    # if email is provided, then first_name and last_name is expected
    # (not required)
    participant_first_name = db.Column(db.String(128))
    participant_last_name = db.Column(db.String(128))
    participant_designation = db.Column(db.String(128))

    sequence_id = db.Column(db.Integer)

    # for mail sent or not
    is_mail_sent = db.Column(db.Boolean, default=False)
    email_status = db.Column(ChoiceString(APP.EMAIL_STATUS_CHOICES),
                             nullable=False, default=APP.EMAIL_NOT_SENT)

    # relationships
    corporate_access_event = db.relationship(
        'CorporateAccessEvent', backref=db.backref(
            'corporate_access_event_participants', passive_deletes=True))
    corporate_external_participant_event = db.relationship(
        'CorporateAccessEvent', backref=db.backref(
            'external_participants', lazy='dynamic',
            passive_deletes=True))
    creator = db.relationship('User', backref=db.backref(
        'corporate_access_event_participants_created', lazy='dynamic'),
        foreign_keys='CorporateAccessEventParticipant.created_by')
    participant = db.relationship('User', backref=db.backref(
        'corporate_access_events_participated', lazy='dynamic'),
        foreign_keys='CorporateAccessEventParticipant.participant_id')
    participant_j = db.relationship(
        'CorporateAccessEvent', secondary='user',
        backref=db.backref('participated', uselist=False),
        foreign_keys=
        '[CorporateAccessEventParticipant.corporate_access_event_id, '
        'CorporateAccessEventParticipant.participant_id, '
        'CorporateAccessEventParticipant.participant_email]',
        primaryjoin=
        'CorporateAccessEvent.row_id == '
        'CorporateAccessEventParticipant.corporate_access_event_id',
        secondaryjoin='or_(CorporateAccessEventParticipant.participant_id == '
                      'User.row_id, '
                      'CorporateAccessEventParticipant.participant_email == '
                      'User.email)',
        viewonly=True)

    # multi column
    __table_args__ = (
        CheckConstraint('((participant_id IS NOT NULL) OR '
                        '(participant_email IS NOT NULL))',
                        name='c_check_caep_participant_id_participant_email_'
                        'not_all_null_key'),
        UniqueConstraint(
            'corporate_access_event_id', 'participant_email',
            name='c_corp_access_evt_id_participant_email_key'),
        UniqueConstraint(
            'corporate_access_event_id', 'participant_id',
            name='c_corp_access_evt_id_participant_id_key'),
        UniqueConstraint(
            'corporate_access_event_id', 'sequence_id',
            name='c_corp_corporate_access_event_id_sequence_id_key')
    )

    def __init__(self, created_by=None, updated_by=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        super(CorporateAccessEventParticipant, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CorporateAccessEventParticipant %r>' % (self.row_id)
