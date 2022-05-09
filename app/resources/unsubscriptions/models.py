"""
Models for "unsubscriptions" package.
"""

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString, ChoiceString
from app.base import constants as APP


class Unsubscription(BaseModel):

    __tablename__ = 'unsubscription'

    email = db.Column(LCString(128), unique=True, nullable=False)

    events = db.Column(db.ARRAY(
        ChoiceString(APP.EVNT_UNSUB_FROM_CHOICES)), default=APP.EVNT_UNSUB_FROM
    )
    # #TODO: add more email types?

    reason_id = db.Column(db.BigInteger, db.ForeignKey(
        'unsubscribe_reason.id', name='unsubscription_reason_id_fkey',
        ondelete='CASCADE'), nullable=False)
    description = db.Column(db.String(1024))

    reason = db.relationship('UnsubscribeReason', backref=db.backref(
        'unsubsriptions', lazy='dynamic'))

    def __init__(self, email=None, *args, **kwargs):
        self.email = email
        super(Unsubscription, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Unsubscription %r>' % (self.email)


class UnsubscribeReason(BaseModel):

    __tablename__ = 'unsubscribe_reason'

    title = db.Column(LCString(512), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    def __init__(self, *args, **kwargs):
        super(UnsubscribeReason, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Unsubscribe reason %r>' % (self.title)
