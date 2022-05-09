"""
Models for "webcast attendees" package.
"""

from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app import db
from app.base.models import BaseModel
from app.base.model_fields import CastingArray
# related model imports done in webcasts/__init__


class WebcastAttendee(BaseModel):

    __tablename__ = 'webcast_attendee'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webcast_attendee_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webcast_attendee_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)
    webcast_id = db.Column(db.BigInteger, db.ForeignKey(
        'webcast.id', name='webcast_attendee_webcast_id_fkey',
        ondelete='CASCADE'), nullable=False)
    attendee_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webcast_attendee_attendee_id_fkey',
        ondelete='CASCADE'), nullable=False)

    rating = db.Column(db.Integer)
    comment = db.Column(db.String(256))

    # fields for big marker api
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
        UniqueConstraint('webcast_id', 'attendee_id',
                         name='c_webcast_id_attendee_id_key'),
    )

    # relationships
    webcast = db.relationship('Webcast', backref=db.backref(
        'webcast_attendee', lazy='dynamic', passive_deletes=True))
    attendee = db.relationship('User', backref=db.backref(
        'webcasts_attended', lazy='dynamic'),
        foreign_keys='WebcastAttendee.attendee_id')

    def __init__(self, created_by=None, webcast_id=None, updated_by=None,
                 attendee_id=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        self.webcast_id = webcast_id
        self.attendee_id = attendee_id
        super(WebcastAttendee, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<WebcastAttendee %r>' % (self.row_id)
