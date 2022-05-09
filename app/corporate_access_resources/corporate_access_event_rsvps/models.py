"""
Models for "corporate access event rsvps" package.
"""

from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString, ChoiceString
from app.base import constants as APP
# related model imports done in corporate_access_resources/__init__


class CorporateAccessEventRSVP(BaseModel):

    __tablename__ = 'corporate_access_event_rsvp'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_rsvp_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_rsvp_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)
    corporate_access_event_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_access_event.id',
        name='corporate_access_event_rsvp_corporate_access_event_id_fkey',
        ondelete='CASCADE'), nullable=False)
    sequence_id = db.Column(db.Integer)

    contact_person = db.Column(db.String(256))
    phone = db.Column(db.String(32))
    email = db.Column(LCString(128))

    is_mail_sent = db.Column(db.Boolean, default=False)
    email_status = db.Column(ChoiceString(APP.EMAIL_STATUS_CHOICES),
                             nullable=False, default=APP.EMAIL_NOT_SENT)

    # relationships
    corporate_access_event = db.relationship(
        'CorporateAccessEvent', backref=db.backref(
            'rsvps', passive_deletes=True))
    creator = db.relationship('User', backref=db.backref(
        'corporate_access_event_rsvps_created', lazy='dynamic'),
        foreign_keys='CorporateAccessEventRSVP.created_by')
    rsvp_j = db.relationship(
        'CorporateAccessEvent', secondary='user',
        backref=db.backref('rsvped', uselist=False),
        foreign_keys=
        '[CorporateAccessEventRSVP.corporate_access_event_id, '
        'CorporateAccessEventRSVP.email]',
        primaryjoin=
        'CorporateAccessEvent.row_id == '
        'CorporateAccessEventRSVP.corporate_access_event_id',
        secondaryjoin='CorporateAccessEventRSVP.email == User.email',
        viewonly=True)

    # multi column
    __table_args__ = (
        UniqueConstraint(
            'corporate_access_event_id', 'sequence_id',
            name='c_corprsvp_corporate_access_event_id_sequence_id_key'),
    )

    def __init__(self, created_by=None, updated_by=None,
                 corporate_access_event_id=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        self.corporate_access_event_id = corporate_access_event_id
        super(CorporateAccessEventRSVP, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CorporateAccessEventRSVP %r>' % (self.row_id)
