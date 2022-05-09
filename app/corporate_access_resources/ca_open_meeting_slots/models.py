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
meeting_disallow_inquiries = db.Table(
    'meeting_disallow_inquiries',
    db.Column('slot_id', db.BigInteger, db.ForeignKey(
        'ca_open_meeting_slot.id', name='open_meeting_disallow_slot_id_fkey',
        ondelete="CASCADE"), nullable=False),
    db.Column('inquired_by', db.Integer, db.ForeignKey(
        'user.id',
        name='disallow_inquired_by_fkey',
        ondelete="CASCADE"), nullable=False),
    UniqueConstraint('slot_id', 'inquired_by',
                     name='ac_open_meeting_slot_id_inquired_by_key'),
)


class CAOpenMeetingSlot(BaseModel):

    __tablename__ = 'ca_open_meeting_slot'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='ca_open_meeting_slot_account_id_fkey',
        ondelete='CASCADE'), nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='ca_open_meeting_slot_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='ca_open_meeting_slot_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)

    event_id = db.Column(db.BigInteger, db.ForeignKey(
        'ca_open_meeting.id',
        name='ca_open_meeting_id_fkey', ondelete='CASCADE'),
        nullable=False)

    slot_type = db.Column(ChoiceString(CA_EVENT_SLOT.CA_EVENT_SLOT_CHOICES),
                          nullable=False, default=CA_EVENT_SLOT.ONE_ON_ONE)
    slot_name = db.Column(db.String(256))
    started_at = db.Column(db.DateTime)
    ended_at = db.Column(db.DateTime)

    bookable_seats = db.Column(db.Integer, default=100)
    booked_seats = db.Column(db.Integer, default=0)
    address = db.Column(db.String(256))
    description = db.Column(db.String(256))
    # fields require in emergency for front end
    text_1 = db.Column(db.String(256))
    text_2 = db.Column(db.String(256))
    # relationships
    ca_open_meeting = db.relationship(
        'CAOpenMeeting', backref=db.backref('slots', passive_deletes=True))
    creator = db.relationship('User', backref=db.backref(
        'ca_open_meeting_slots_created', lazy='dynamic'),
        foreign_keys='CAOpenMeetingSlot.created_by')
    account = db.relationship('Account', backref=db.backref(
        'ca_open_meeting_slots', lazy='dynamic'))

    disallowed = db.relationship(
        'User', secondary=meeting_disallow_inquiries, backref=db.backref(
            'meeting_disallowed_slots', lazy='dynamic'),
        passive_deletes=True)
    inquiry_histories = db.relationship(
        'CAOpenMeetingInquiryHistory',
        secondary='ca_open_meeting', backref=db.backref(
            'inquiry_rejected', uselist=False),
        foreign_keys='[CAOpenMeetingSlot.row_id,'
                     'CAOpenMeetingSlot.event_id]',
        primaryjoin="and_(CAOpenMeetingInquiryHistory.status =='" +
                    INQUIRY.DELETED + "', "
                    "CAOpenMeetingInquiryHistory."
                    "ca_open_meeting_slot_id == "
                    "CAOpenMeetingSlot.row_id)",
        secondaryjoin="CAOpenMeeting.row_id == "
                      "CAOpenMeetingSlot.event_id",
        viewonly=True)

    def __init__(self, created_by=None, updated_by=None,
                 account_id=None, event_id=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        self.account_id = account_id
        self.event_id = event_id
        super(CAOpenMeetingSlot, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CAOpenMeetingSlot %r>' % (self.row_id)
