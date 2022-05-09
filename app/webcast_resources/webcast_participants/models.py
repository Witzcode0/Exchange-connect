"""
Models for "webcast participants" package.
"""

from sqlalchemy import CheckConstraint, UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString, ChoiceString
from app.base import constants as APP
# related model imports done in webcasts/__init__


class WebcastParticipant(BaseModel):

    __tablename__ = 'webcast_participant'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webcast_participant_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webcast_participant_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)

    webcast_id = db.Column(db.BigInteger, db.ForeignKey(
        'webcast.id', name='webcast_participant_webcast_id_fkey',
        ondelete='CASCADE'), nullable=False)
    participant_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webcast_participant_participant_id_fkey',
        ondelete='CASCADE'))
    sequence_id = db.Column(db.Integer)
    participant_email = db.Column(LCString(128))
    is_mail_sent = db.Column(db.Boolean, default=False)
    email_status = db.Column(ChoiceString(APP.EMAIL_STATUS_CHOICES),
                             nullable=False, default=APP.EMAIL_NOT_SENT)
    # if email is provided, then first_name and last_name is expected
    # (not required)
    participant_first_name = db.Column(db.String(128))
    participant_last_name = db.Column(db.String(128))
    participant_designation = db.Column(db.String(128))

    # url for bigmarker conference
    conference_url = db.Column(db.String(256))

    # multi column
    __table_args__ = (
        CheckConstraint('((participant_id IS NOT NULL) OR '
                        '(participant_email IS NOT NULL))',
                        name='c_check_wbcpr_participant_id_participant_email_'
                        'not_all_null_key'),
        UniqueConstraint('webcast_id', 'participant_email',
                         name='c_webcast_id_participant_email_key'),
        UniqueConstraint('webcast_id', 'participant_id',
                         name='c_webcast_id_participant_id_key'),
        UniqueConstraint('webcast_id', 'sequence_id',
                         name='c_webcast_id_sequence_id_key')
    )

    # relationships
    webcast = db.relationship('Webcast', backref=db.backref(
        'webcast_participants', lazy='dynamic', passive_deletes=True))
    creator = db.relationship('User', backref=db.backref(
        'webcasts_created', lazy='dynamic'),
        foreign_keys='WebcastParticipant.created_by')
    participant = db.relationship('User', backref=db.backref(
        'webcasts_participated', lazy='dynamic'),
        foreign_keys='WebcastParticipant.participant_id')
    webcast_external_participants = db.relationship(
        'Webcast', backref=db.backref('external_participants', lazy='dynamic',
                                      passive_deletes=True))

    def __init__(self, created_by=None, updated_by=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        super(WebcastParticipant, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<WebcastParticipant %r>' % (self.row_id)
