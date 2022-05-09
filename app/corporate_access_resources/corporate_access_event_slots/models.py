"""
Models for "corporate access event slots" package.
"""

from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString
from app.corporate_access_resources.corporate_access_event_slots import \
    constants as CA_EVENT_SLOT
from app.corporate_access_resources.corporate_access_event_inquiries import \
    constants as INQUIRY
# related model imports done in corporate_access_resources/__init__


# association table for many-to-many slot and inquiry
disallow_inquiries = db.Table(
    'disallow_inquiries',
    db.Column('slot_id', db.BigInteger, db.ForeignKey(
        'corporate_access_event_slot.id', name='disallow_slot_id_fkey',
        ondelete="CASCADE"), nullable=False),
    db.Column('inquired_by', db.Integer, db.ForeignKey(
        'user.id',
        name='disallow_inquired_by_fkey',
        ondelete="CASCADE"), nullable=False),
    UniqueConstraint('slot_id', 'inquired_by',
                     name='ac_slot_id_inquired_by_key'),
)


class CorporateAccessEventSlot(BaseModel):

    __tablename__ = 'corporate_access_event_slot'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='corporate_access_event_slot_account_id_fkey',
        ondelete='CASCADE'), nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_slot_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_slot_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)

    event_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_access_event.id',
        name='corporate_access_event_slot_event_id_fkey', ondelete='CASCADE'),
        nullable=False)

    slot_type = db.Column(ChoiceString(CA_EVENT_SLOT.CA_EVENT_SLOT_CHOICES),
                          nullable=False, default=CA_EVENT_SLOT.ONE_ON_ONE)
    slot_name = db.Column(db.String(256))
    started_at = db.Column(db.DateTime)
    ended_at = db.Column(db.DateTime)

    bookable_seats = db.Column(db.Integer, default=0)
    booked_seats = db.Column(db.Integer, default=0)
    address = db.Column(db.String(256))
    description = db.Column(db.String(256))
    # fields require in emergency for front end
    text_1 = db.Column(db.String(256))
    text_2 = db.Column(db.String(256))
    # relationships
    corporate_access_event = db.relationship(
        'CorporateAccessEvent', backref=db.backref(
            'slots', lazy='dynamic',
            passive_deletes=True))
    creator = db.relationship('User', backref=db.backref(
        'corporate_access_event_slots_created', lazy='dynamic'),
        foreign_keys='CorporateAccessEventSlot.created_by')
    account = db.relationship('Account', backref=db.backref(
        'corporate_access_event_slots', lazy='dynamic'))

    disallowed = db.relationship(
        'User', secondary=disallow_inquiries, backref=db.backref(
            'disallowed_slots', lazy='dynamic'),
        passive_deletes=True)
    inquiry_histories = db.relationship(
        'CorporateAccessEventInquiryHistory',
        secondary='corporate_access_event', backref=db.backref(
            'inquiry_rejected', uselist=False),
        foreign_keys='[CorporateAccessEventSlot.row_id,'
                     'CorporateAccessEventSlot.event_id]',
        primaryjoin="and_(CorporateAccessEventInquiryHistory.status =='" +
                    INQUIRY.DELETED + "', "
                    "CorporateAccessEventInquiryHistory."
                    "corporate_access_event_slot_id == "
                    "CorporateAccessEventSlot.row_id)",
        secondaryjoin="CorporateAccessEvent.row_id == "
                      "CorporateAccessEventSlot.event_id",
        viewonly=True)

    def __init__(self, created_by=None, updated_by=None,
                 account_id=None, event_id=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        self.account_id = account_id
        self.event_id = event_id
        super(CorporateAccessEventSlot, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CorporateAccessEventSlot %r>' % (self.row_id)
