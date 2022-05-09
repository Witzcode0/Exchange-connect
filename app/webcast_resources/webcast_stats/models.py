"""
Models for "webcast stats" package.
"""

from app import db
from app.base.models import BaseModel
# related model imports done in webcasts/__init__


class WebcastStats(BaseModel):

    __tablename__ = 'webcast_stats'

    webcast_id = db.Column(db.BigInteger, db.ForeignKey(
        'webcast.id', name='webcast_stats_webcast_id_fkey',
        ondelete='CASCADE'), nullable=False)

    total_participants = db.Column(db.BigInteger, default=0)
    total_hosts = db.Column(db.BigInteger, default=0)
    total_rsvps = db.Column(db.BigInteger, default=0)
    total_invitees = db.Column(db.BigInteger, default=0)
    total_attendees = db.Column(db.BigInteger, default=0)
    total_questions = db.Column(db.BigInteger, default=0)
    total_answers = db.Column(db.BigInteger, default=0)
    average_rating = db.Column(db.Numeric(5, 2), default=0.00)
    total_files = db.Column(db.BigInteger, default=0)

    # relationships
    webcast = db.relationship('Webcast', backref=db.backref(
        'stats', uselist=False, passive_deletes=True),
        primaryjoin='WebcastStats.webcast_id == Webcast.row_id')

    def __init__(self, webcast_id=None, *args, **kwargs):
        self.webcast_id = webcast_id
        super(WebcastStats, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<WebcastStats %r>' % (self.webcast_id)
