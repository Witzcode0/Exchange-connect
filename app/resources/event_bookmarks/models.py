"""
Models for "event bookmarks" package.
"""

from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.resources.events.models import Event


class EventBookmark(BaseModel):

    __tablename__ = 'event_bookmark'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='event_bookmark_account_id_fkey',
        ondelete='CASCADE'), nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='event_bookmark_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    event_id = db.Column(db.BigInteger, db.ForeignKey(
        'event.id', name='event_bookmark_event_id_fkey', ondelete='CASCADE'),
        nullable=False)

    # multi column
    __table_args__ = (
        UniqueConstraint('created_by', 'event_id',
                         name='c_created_by_event_id_key'),
    )

    # relationships
    account = db.relationship('Account', backref=db.backref(
        'event_bookmarks', lazy='dynamic'))
    creator = db.relationship('User', backref=db.backref(
        'event_bookmarks', lazy='dynamic'),
        foreign_keys='EventBookmark.created_by')
    event = db.relationship('Event', backref=db.backref(
        'event_bookmarks', lazy='dynamic'))
    # special relationship for already starred eager loading check
    events_j = db.relationship('Event', backref=db.backref(
        'event_bookmarked', uselist=False))

    def __init__(self, event_id=None, *args, **kwargs):
        self.event_id = event_id
        super(EventBookmark, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<EventBookmark %r>' % (self.row_id)
