"""
Models for "corporate access ref event types" package.
"""

from sqlalchemy import func, Index

from app import db
from app.base.models import BaseModel


class CARefEventType(BaseModel):

    __tablename__ = 'corporate_access_ref_event_type'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_ref_event_type_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_ref_event_type_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)

    name = db.Column(db.String(128), unique=True, nullable=False)
    description = db.Column(db.String(256))
    # for one-to-one meeting
    is_meeting = db.Column(db.Boolean, default=False)

    deleted = db.Column(db.Boolean, default=False)

    __table_args__ = (
        # unique lower case index, i.e case-insensitive unique constraint
        Index('ci_corporate_access_ref_event_type_unique_name', func.lower(
            name), unique=True),
    )

    # relationships
    creator = db.relationship('User', backref=db.backref(
        'corporate_access_ref_event_types_created', lazy='dynamic'),
        foreign_keys='CARefEventType.created_by')

    def __init__(self, created_by=None, updated_by=None,
                 *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        super(CARefEventType, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CARefEventType %r>' % (self.row_id)
