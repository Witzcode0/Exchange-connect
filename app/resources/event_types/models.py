"""
Model for event type
"""

from sqlalchemy import func, Index

from app import db
from app.base.models import BaseModel


class EventType(BaseModel):

    __tablename__ = 'event_type'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='event_type_account_id_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='event_type_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='event_type_created_by_fkey', ondelete='CASCADE'),
        nullable=False)

    name = db.Column(db.String(256), nullable=False)

    deleted = db.Column(db.Boolean, default=False)
    activated = db.Column(db.Boolean, default=True)  # in future

    __table_args__ = (
        # unique lower case index, i.e case-insensitive unique constraint
        Index('ci_event_type_unique_name', func.lower(name), unique=True),
    )

    def __init__(self, name=None, *args, **kwargs):
        self.name = name
        super(EventType, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<EventType %r>' % (self.row_id)
