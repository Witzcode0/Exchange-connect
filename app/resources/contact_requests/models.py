"""
Models for "contact requests" package.
"""

from app import db
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString
from app.resources.contact_requests import constants as CONREQUEST
from app.resources.users.models import User
from app.resources.user_profiles.models import UserProfile


class ContactRequest(BaseModel):

    __tablename__ = 'contact_request'

    sent_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='contact_request_sent_by_fkey', ondelete='CASCADE'),
        nullable=False)
    sent_to = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='contact_request_sent_to_fkey', ondelete='CASCADE'),
        nullable=False)
    status = db.Column(ChoiceString(CONREQUEST.CREQ_STATUS_TYPE_CHOICES),
                       nullable=False, default=CONREQUEST.CRT_SENT)
    message = db.Column(db.String(1024))
    # requested_on is created_date in basemodel
    accepted_rejected_on = db.Column(db.DateTime)

    sender = db.relationship('User', backref=db.backref(
        'contact_requests_sent', lazy='dynamic'),
        foreign_keys='ContactRequest.sent_by')
    sendee = db.relationship('User', backref=db.backref(
        'contact_requests_received', lazy='dynamic'),
        foreign_keys='ContactRequest.sent_to')
    # special relationship for already contact requested eager loading check
    contact_requested_j = db.relationship('UserProfile', backref=db.backref(
        'contact_requested', uselist=False),
        foreign_keys='[ContactRequest.sent_by, ContactRequest.sent_to]',
        primaryjoin="and_(ContactRequest.status == '" + CONREQUEST.CRT_SENT +
        "', ContactRequest.accepted_rejected_on == None, "
        "or_(UserProfile.user_id == ContactRequest.sent_by, "
        "UserProfile.user_id == ContactRequest.sent_to))")
    # dynamic properties
    the_other = None  # the other user when checking contacts for a user

    def __init__(self, sent_by=None, sent_to=None, status=None,
                 *args, **kwargs):
        self.sent_by = sent_by
        self.sent_to = sent_to
        self.status = status
        super(ContactRequest, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<ContactRequest %r>' % (self.sent_by)


class ContactRequestHistory(BaseModel):
    """
    Maintains a contact request history, incase of deletions of contact request
    or contact.
    """

    __tablename__ = 'contact_request_history'

    sent_by = db.Column(db.BigInteger, nullable=False)
    sent_to = db.Column(db.BigInteger, nullable=False)
    status = db.Column(ChoiceString(CONREQUEST.CREQ_STATUS_TYPE_CHOICES),
                       nullable=False)
    # requested_on is created_date in basemodel
    accepted_rejected_on = db.Column(db.DateTime)

    def __init__(self, sent_by=None, sent_to=None, status=None,
                 *args, **kwargs):
        self.sent_by = sent_by
        self.sent_to = sent_to
        self.status = status
        super(ContactRequestHistory, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<ContactRequestHistory %r>' % (self.sent_by)
