"""
Models for "webinar attendees" package.
"""

from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app import db
from app.base.models import BaseModel
from app.base.model_fields import CastingArray, LCString
# related model imports done in webinars/__init__


class WebinarAttendee(BaseModel):

    __tablename__ = 'webinar_attendee'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webinar_attendee_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webinar_attendee_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)
    webinar_id = db.Column(db.BigInteger, db.ForeignKey(
        'webinar.id', name='webinar_attendee_webinar_id_fkey',
        ondelete='CASCADE'), nullable=False)
    attendee_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webinar_attendee_attendee_id_fkey',
        ondelete='CASCADE'))
    attendee_email = db.Column(LCString(128))
    attendee_first_name = db.Column(db.String(128))
    attendee_last_name = db.Column(db.String(128))

    rating = db.Column(db.Integer)
    comment = db.Column(db.String(256))

    # fields for third party api
    entered_at = db.Column(db.DateTime)
    leaved_at = db.Column(db.DateTime)
    total_duration = db.Column(db.String(16))
    engaged_duration = db.Column(db.String(16))
    chats_count = db.Column(db.BigInteger())
    qas_count = db.Column(db.BigInteger())
    polls_count = db.Column(db.BigInteger())
    polls = db.Column(CastingArray(JSONB))
    questions = db.Column(db.ARRAY(db.String()))
    handouts = db.Column(db.ARRAY(db.String()))
    browser_name = db.Column(db.String(128))
    browser_version = db.Column(db.String(128))
    device_name = db.Column(db.String(128))

    # multi column
    __table_args__ = (
        UniqueConstraint('webinar_id', 'attendee_id',
                         name='c_webinar_id_attendee_id_key'),
    )

    # relationships
    webinar = db.relationship('Webinar', backref=db.backref(
        'webinar_attendee', lazy='dynamic', passive_deletes=True))
    attendee = db.relationship('User', backref=db.backref(
        'webinars_attended', lazy='dynamic'),
        foreign_keys='WebinarAttendee.attendee_id')

    def __init__(self, webinar_id=None, attendee_id=None, created_by=None,
                 updated_by=None, *args, **kwargs):
        self.webinar_id = webinar_id
        self.attendee_id = attendee_id
        self.created_by = created_by
        self.updated_by = updated_by
        super(WebinarAttendee, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<WebinarAttendee %r>' % (self.row_id)
