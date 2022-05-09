"""
Models for "contacts" package.
"""

from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.resources.users.models import User


class Contact(BaseModel):
    """
    Connects 2 users as contacts
    """

    __tablename__ = 'contact'

    sent_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='contact_sent_by_fkey', ondelete='CASCADE'),
        nullable=False)
    sent_to = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='contact_sent_to_fkey', ondelete='CASCADE'),
        nullable=False)

    sender = db.relationship('User', backref=db.backref(
        'contact_sent', lazy='dynamic'), foreign_keys='Contact.sent_by')
    sendee = db.relationship('User', backref=db.backref(
        'contact_received', lazy='dynamic'), foreign_keys='Contact.sent_to')
    # special relationship for already connected eager loading check
    connected_j = db.relationship('UserProfile', backref=db.backref(
        'connected', uselist=False),
        foreign_keys='[Contact.sent_by, Contact.sent_to]',
        primaryjoin='or_(UserProfile.user_id == Contact.sent_by, '
        'UserProfile.user_id == Contact.sent_to)', viewonly=True)

    # multi column
    __table_args__ = (
        UniqueConstraint('sent_by', 'sent_to', name='c_sent_by_sent_to_key'),
    )

    # dynamic properties
    the_other = None  # the other user when checking contacts for a user

    def __init__(self, sent_by=None, sent_to=None, *args, **kwargs):
        self.sent_by = sent_by
        self.sent_to = sent_to
        super(Contact, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Contact %r>' % (self.sent_by)


class ContactHistory(BaseModel):
    """
    Maintains a contact history, incase of deletions.
    """

    __tablename__ = 'contact_history'

    sent_by = db.Column(db.BigInteger, nullable=False)
    sent_to = db.Column(db.BigInteger, nullable=False)

    def __init__(self, sent_by=None, sent_to=None, *args, **kwargs):
        self.sent_by = sent_by
        self.sent_to = sent_to
        super(ContactHistory, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<ContactHistory %r>' % (self.sent_by)
