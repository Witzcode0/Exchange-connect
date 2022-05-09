"""
Models for "webcast rsvps" package.
"""

from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString, ChoiceString
from app.base import constants as APP
# related model imports done in webcasts/__init__


class WebcastRSVP(BaseModel):

    __tablename__ = 'webcast_rsvp'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webcast_rsvp_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webcast_rsvp_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)
    webcast_id = db.Column(db.BigInteger, db.ForeignKey(
        'webcast.id', name='webcast_rsvp_webcast_id_fkey',
        ondelete='CASCADE'), nullable=False)
    sequence_id = db.Column(db.Integer)
    contact_person = db.Column(db.String(256))
    phone = db.Column(db.String(32))
    email = db.Column(LCString(128))
    is_mail_sent = db.Column(db.Boolean, default=False)
    email_status = db.Column(ChoiceString(APP.EMAIL_STATUS_CHOICES),
                             nullable=False, default=APP.EMAIL_NOT_SENT)

    # url for bigmarker conference
    conference_url = db.Column(db.String(256))

    # multi column
    __table_args__ = (
        UniqueConstraint(
            'webcast_id', 'sequence_id',
            name='c_wbcnrp_webcast_id_sequence_id_key'),
    )

    # relationships
    webcast = db.relationship('Webcast', backref=db.backref(
        'rsvps', lazy='dynamic', passive_deletes=True))
    creator = db.relationship('User', backref=db.backref(
        'webcast_rsvps_created', lazy='dynamic'),
        foreign_keys='WebcastRSVP.created_by')

    def __init__(self, created_by=None, updated_by=None,
                 webcast_id=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        self.webcast_id = webcast_id
        super(WebcastRSVP, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<WebcastRSVP %r>' % (self.row_id)
