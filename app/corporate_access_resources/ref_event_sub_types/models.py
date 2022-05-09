"""
Models for "corporate access ref event sub types" package.
"""

from sqlalchemy import func, Index

from app import db
from app.base.models import BaseModel


class CARefEventSubType(BaseModel):

    __tablename__ = 'corporate_access_ref_event_sub_type'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_ref_event_sub_type_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_ref_event_sub_type_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)

    event_type_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_access_ref_event_type.id',
        name='corporate_access_ref_event_sub_type_event_type_id_fkey',
        ondelete='CASCADE'), nullable=False)

    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(256))

    has_slots = db.Column(db.Boolean, default=True)

    deleted = db.Column(db.Boolean, default=False)

    show_time = db.Column(db.Boolean, default=False)  # for date time in email

    __table_args__ = (
        # unique lower case index, i.e case-insensitive unique constraint
        Index('ci_corporate_access_ref_event_sub_type_unique_type_id_name',
              event_type_id, func.lower(name), unique=True),
    )

    # relationships
    creator = db.relationship('User', backref=db.backref(
        'corporate_access_ref_event_sub_types_created', lazy='dynamic'),
        foreign_keys='CARefEventSubType.created_by')
    event_type = db.relationship('CARefEventType', backref=db.backref(
        'corporate_access_ref_event_sub_types', lazy='dynamic'))

    def __init__(self, created_by=None, updated_by=None,
                 event_type_id=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        self.event_type_id = event_type_id
        super(CARefEventSubType, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CARefEventSubType %r>' % (self.row_id)
