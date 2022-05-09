"""
Models for "webinar chats" package.
"""

from app import db
from app.base.models import BaseModel
# related model imports done in webinars/__init__


class WebinarChatMessage(BaseModel):

    __tablename__ = 'webinar_chat_message'

    webinar_id = db.Column(db.BigInteger, db.ForeignKey(
        'webinar.id', name='webinar_chat_message_webinar_id_fkey',
        ondelete='CASCADE'), nullable=False)
    sent_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webinar_chat_message_sent_by_fkey',
        ondelete='CASCADE'), nullable=False)

    message = db.Column(db.String(1024))
    sent_to = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webinar_chat_message_sent_to_fkey',
        ondelete='SET NULL'))
    in_reply_to = db.Column(db.BigInteger, db.ForeignKey(
        'webinar_chat_message.id',
        name='webinar_chat_message_in_reply_to_fkey', ondelete='SET NULL'))

    # relationships
    webinar = db.relationship('Webinar', backref=db.backref(
        'webinar_chats', lazy='dynamic', passive_deletes=True))
    sender = db.relationship('User', backref=db.backref(
        'webinar_chats', lazy='dynamic'),
        foreign_keys='WebinarChatMessage.sent_by')

    def __init__(self, webinar_id=None, sent_by=None, *args, **kwargs):
        self.webinar_id = webinar_id
        self.sent_by = sent_by
        super(WebinarChatMessage, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<WebinarChatMessage %r>' % (self.row_id)
