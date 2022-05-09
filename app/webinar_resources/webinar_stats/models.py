"""
Models for "webinar stats" package.
"""

from app import db
from app.base.models import BaseModel
# related model imports done in webinars/__init__


class WebinarStats(BaseModel):

    __tablename__ = 'webinar_stats'

    webinar_id = db.Column(db.BigInteger, db.ForeignKey(
        'webinar.id', name='webinar_stats_webinar_id_fkey',
        ondelete='CASCADE'), nullable=False)

    total_participants = db.Column(db.BigInteger, default=0)
    total_hosts = db.Column(db.BigInteger, default=0)
    total_rsvps = db.Column(db.BigInteger, default=0)
    total_invitees = db.Column(db.BigInteger, default=0)
    total_attendees = db.Column(db.BigInteger, default=0)
    total_chat_messages = db.Column(db.BigInteger, default=0)
    total_questions = db.Column(db.BigInteger, default=0)
    total_answers = db.Column(db.BigInteger, default=0)
    average_rating = db.Column(db.Numeric(5, 2), default=0.00)
    total_files = db.Column(db.BigInteger, default=0)

    # relationships
    webinar = db.relationship('Webinar', backref=db.backref(
        'stats', uselist=False, passive_deletes=True),
        primaryjoin='WebinarStats.webinar_id == Webinar.row_id')

    def __init__(self, webinar_id=None, *args, **kwargs):
        self.webinar_id = webinar_id
        super(WebinarStats, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<WebinarStats %r>' % (self.webinar_id)
