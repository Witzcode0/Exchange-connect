"""
Models for "webinar participants" package.
"""

from sqlalchemy import CheckConstraint, UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString, ChoiceString
from app.base import constants as APP
# related model imports done in webinars/__init__


class WebinarParticipant(BaseModel):

    __tablename__ = 'webinar_participant'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webinar_participant_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webinar_participant_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)

    webinar_id = db.Column(db.BigInteger, db.ForeignKey(
        'webinar.id', name='webinar_participant_webinar_id_fkey',
        ondelete='CASCADE'), nullable=False)
    sequence_id = db.Column(db.Integer)  # , nullable=False)

    participant_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webinar_participant_participant_id_fkey',
        ondelete='CASCADE'))
    participant_email = db.Column(LCString(128))
    # if email is provided, then first_name and last_name is expected
    # (not required)
    participant_first_name = db.Column(db.String(128))
    participant_last_name = db.Column(db.String(128))
    participant_designation = db.Column(db.String(128))

    is_mail_sent = db.Column(db.Boolean, default=False)
    email_status = db.Column(ChoiceString(APP.EMAIL_STATUS_CHOICES),
        nullable=False, default=APP.EMAIL_NOT_SENT)
    # url for bigmarker conference
    conference_url = db.Column(db.String(256))

    # relationships
    webinar = db.relationship('Webinar', backref=db.backref(
        'webinar_participants', lazy='dynamic', passive_deletes=True))
    creator = db.relationship('User', backref=db.backref(
        'webinars_created', lazy='dynamic'),
        foreign_keys='WebinarParticipant.created_by')
    participant = db.relationship('User', backref=db.backref(
        'webinars_participated', lazy='dynamic'),
        foreign_keys='WebinarParticipant.participant_id')
    external_participant = db.relationship('Webinar', backref=db.backref(
        'external_participants', lazy='dynamic', passive_deletes=True))

    # multi column
    __table_args__ = (
        CheckConstraint('((participant_id IS NOT NULL) OR '
                        '(participant_email IS NOT NULL))',
                        name='c_check_wbnpr_participant_id_participant_email_'
                        'not_all_null_key'),
        UniqueConstraint(
            'webinar_id', 'participant_email',
            name='c_webinar_id_participant_email_key'),
        UniqueConstraint(
            'webinar_id', 'participant_id',
            name='c_webinar_id_participant_id_key'),
        UniqueConstraint(
            'webinar_id', 'sequence_id',
            name='c_wbnpr_webinar_id_sequence_id_key')
    )

    def __init__(self, created_by=None, updated_by=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        super(WebinarParticipant, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<WebinarParticipant %r>' % (self.row_id)
