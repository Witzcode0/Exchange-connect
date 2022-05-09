"""
Models for "corporate access event inquiries" package.
"""

from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString
from app.corporate_access_resources.corporate_access_event_inquiries import \
    constants as CA_EVENT_INQUIRY
# related model imports done in corporate_access_resources/__init__


class CorporateAccessEventInquiry(BaseModel):

    __tablename__ = 'corporate_access_event_inquiry'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_inquiry_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_inquiry_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)

    corporate_access_event_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_access_event.id',
        name='corporate_access_event_inquiry_corporate_access_event_id_fkey',
        ondelete='CASCADE'), nullable=False)
    corporate_access_event_slot_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_access_event_slot.id',
        name='cracs_event_inquiry_corporate_access_event_slot_id_fkey',
        ondelete='CASCADE'), nullable=False)

    status = db.Column(ChoiceString(
        CA_EVENT_INQUIRY.CA_EVENT_INQUIRY_STATUS_CHOICES),
        nullable=False, default=CA_EVENT_INQUIRY.INQUIRED)

    # relationships
    corporate_access_event = db.relationship(
        'CorporateAccessEvent', backref=db.backref(
            'corporate_access_event_inquiries', lazy='dynamic',
            passive_deletes=True))
    corporate_access_event_slot = db.relationship(
        'CorporateAccessEventSlot', backref=db.backref(
            'corporate_access_event_inquiries', lazy='dynamic',
            passive_deletes=True))
    creator = db.relationship('User', backref=db.backref(
        'corporate_access_event_inquiries', lazy='dynamic'),
        foreign_keys='CorporateAccessEventInquiry.created_by')

    __table_args__ = (
        UniqueConstraint('created_by', 'corporate_access_event_id',
                         'corporate_access_event_slot_id',
                         name='c_event_id_slot_id_created_by_key'),
    )

    def __init__(self, created_by=None, updated_by=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        super(CorporateAccessEventInquiry, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CorporateAccessEventInquiry %r>' % (self.row_id)


class CorporateAccessEventInquiryHistory(BaseModel):

    __tablename__ = 'corporate_access_event_inquiry_history'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_inquiry_his_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, nullable=False)

    corporate_access_event_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_access_event.id',
        name='corporate_access_event_inq_his_corporate_access_event_id_fkey'),
        nullable=False)
    corporate_access_event_slot_id = db.Column(db.BigInteger, nullable=False)

    status = db.Column(ChoiceString(
        CA_EVENT_INQUIRY.CA_HIS_EVENT_INQUIRY_STATUS_CHOICES),
        nullable=False, default=CA_EVENT_INQUIRY.INQUIRED)

    creator = db.relationship('User', backref=db.backref(
        'corporate_access_event_inquiry_history', lazy='dynamic'),
        foreign_keys='CorporateAccessEventInquiryHistory.created_by')

    def __init__(self, created_by=None, updated_by=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        super(CorporateAccessEventInquiryHistory, self).__init__(
            *args, **kwargs)

    def __repr__(self):
        return '<CorporateAccessEventInquiryHistory %r>' % (self.row_id)
