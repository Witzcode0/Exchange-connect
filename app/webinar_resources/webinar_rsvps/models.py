"""
Models for "webinar rsvps" package.
"""
from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString, ChoiceString
from app.base import constants as APP
# related model imports done in webinars/__init__


class WebinarRSVP(BaseModel):

    __tablename__ = 'webinar_rsvp'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webinar_rsvp_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webinar_rsvp_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)

    webinar_id = db.Column(db.BigInteger, db.ForeignKey(
        'webinar.id', name='webinar_rsvp_webinar_id_fkey',
        ondelete='CASCADE'), nullable=False)
    sequence_id = db.Column(db.Integer)  # , nullable=False)

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
            'webinar_id', 'sequence_id',
            name='c_wbnrp_webinar_id_sequence_id_key'),
    )

    # relationships
    webinar = db.relationship('Webinar', backref=db.backref(
        'rsvps', lazy='dynamic', passive_deletes=True))
    creator = db.relationship('User', backref=db.backref(
        'webinar_rsvps_created', lazy='dynamic'),
        foreign_keys='WebinarRSVP.created_by')

    def __init__(self, created_by=None, updated_by=None,
                 webinar_id=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        self.webinar_id = webinar_id
        super(WebinarRSVP, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<WebinarRSVP %r>' % (self.row_id)
