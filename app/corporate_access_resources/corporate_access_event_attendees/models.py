"""
Models for "corporate access event attendees" package.
"""

from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.corporate_access_resources.corporate_access_event_inquiries \
    import constants as INQUIRY
# related model imports done in corporate_access_resources/__init__


class CorporateAccessEventAttendee(BaseModel):

    __tablename__ = 'corporate_access_event_attendee'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_attendee_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_attendee_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)
    corporate_access_event_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_access_event.id',
        name='corporate_access_event_attendee_corporate_access_event_id_fkey',
        ondelete='CASCADE'), nullable=False)
    attendee_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_attendee_attendee_id_fkey',
        ondelete='CASCADE'))

    invitee_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_access_event_invitee.id',
        name='corporate_access_event_attendee_invitee_id_fkey',
        ondelete='CASCADE'))

    corporate_access_event_slot_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_access_event_slot.id',
        name='cracs_event_attendee_corporate_access_event_slot_id_fkey',
        ondelete='SET NULL'))

    rating = db.Column(db.Integer)
    comment = db.Column(db.String(256))

    # multi column
    __table_args__ = (
        UniqueConstraint(
            'corporate_access_event_id', 'corporate_access_event_slot_id',
            'attendee_id',
            name='c_cracs_event_id_corporate_access_event_slot_id_'
            'attendee_id_key'),  # postgres identifier limit of 63
        UniqueConstraint(
            'corporate_access_event_id', 'attendee_id',
            name='c_cracs_event_id_attendee_id_key'
        ),
        UniqueConstraint(
            'corporate_access_event_id', 'invitee_id',
            name='c_cracs_event_id_invitee_id_key'
        )
    )

    # relationships
    corporate_access_event = db.relationship(
        'CorporateAccessEvent', backref=db.backref(
            'corporate_access_event_attendee', lazy='dynamic',
            passive_deletes=True))
    corporate_access_event_slot = db.relationship(
        'CorporateAccessEventSlot', backref=db.backref(
            'corporate_access_event_slot_attendee', lazy='dynamic'))

    attendee = db.relationship('User', backref=db.backref(
        'corporate_access_events_attended', lazy='dynamic'),
        foreign_keys='CorporateAccessEventAttendee.attendee_id')

    guest_invitee = db.relationship(
        'CorporateAccessEventInvitee', backref=db.backref(
            'corporate_access_invitee_attended'))

    attendee_j = db.relationship(
        'CorporateAccessEventInquiry', backref=db.backref(
            'attended', uselist=False),
        foreign_keys='[CorporateAccessEventAttendee.corporate_access_event_id,'
                     'CorporateAccessEventAttendee.attendee_id, '
                     'CorporateAccessEventAttendee.'
                     'corporate_access_event_slot_id]',
        primaryjoin="and_(CorporateAccessEventInquiry.status == '" +
                    INQUIRY.CONFIRMED +
                    "', CorporateAccessEventAttendee."
                    "corporate_access_event_id"
                    "== CorporateAccessEventInquiry.corporate_access_event_id,"
                    "CorporateAccessEventAttendee.attendee_id == "
                    "CorporateAccessEventInquiry.created_by, "
                    "CorporateAccessEventAttendee."
                    "corporate_access_event_slot_id == "
                    "CorporateAccessEventInquiry."
                    "corporate_access_event_slot_id)")

    def __init__(self, corporate_access_event_id=None, attendee_id=None,
                 created_by=None, updated_by=None, *args, **kwargs):
        self.corporate_access_event_id = corporate_access_event_id
        self.attendee_id = attendee_id
        self.created_by = created_by
        self.updated_by = updated_by
        super(CorporateAccessEventAttendee, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CorporateAccessEventAttendee %r>' % (self.row_id)
