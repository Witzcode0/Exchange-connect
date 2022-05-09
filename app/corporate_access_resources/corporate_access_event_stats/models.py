"""
Models for "corporate access events stats" package.
"""

from app import db
from app.base.models import BaseModel
# related model imports done in corporate_access_resources/__init__
# ^ required for relationship


class CorporateAccessEventStats(BaseModel):

    __tablename__ = 'corporate_access_event_stats'

    corporate_access_event_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_access_event.id',
        name='corpacc_event_stats_corporate_access_event_id_fkey',
        ondelete='CASCADE'), nullable=False)

    total_participants = db.Column(db.BigInteger, default=0)
    total_hosts = db.Column(db.BigInteger, default=0)
    total_rsvps = db.Column(db.BigInteger, default=0)
    total_collaborators = db.Column(db.BigInteger, default=0)
    total_slots = db.Column(db.BigInteger, default=0)
    total_agendas = db.Column(db.BigInteger, default=0)
    total_non_slot_meetings = db.Column(db.BigInteger, default=0)
    total_seats = db.Column(db.BigInteger, default=0)
    total_booked = db.Column(db.BigInteger, default=0)
    total_invitees = db.Column(db.BigInteger, default=0)
    total_joined = db.Column(db.BigInteger, default=0)
    total_inquiries = db.Column(db.BigInteger, default=0)
    total_attended = db.Column(db.BigInteger, default=0)
    total_files = db.Column(db.BigInteger, default=0)
    average_rating = db.Column(db.Numeric(5, 2), default=0.00)

    # relationships
    event = db.relationship('CorporateAccessEvent', backref=db.backref(
        'stats', uselist=False, passive_deletes=True),
        primaryjoin='CorporateAccessEventStats.corporate_access_event_id '
        '== CorporateAccessEvent.row_id')

    def __init__(self, corporate_access_event_id=None, *args, **kwargs):
        self.corporate_access_event_id = corporate_access_event_id
        super(CorporateAccessEventStats, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CorporateAccessEventStats %r>' % (
            self.corporate_access_event_id)
