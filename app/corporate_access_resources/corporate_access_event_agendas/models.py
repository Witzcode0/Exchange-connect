"""
Models for "corporate access event agendas" package.
"""


from app import db
from app.base.models import BaseModel
# related model imports done in corporate_access_resources/__init__


class CorporateAccessEventAgenda(BaseModel):

    __tablename__ = 'corporate_access_event_agenda'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_agenda_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_agenda_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)

    corporate_access_event_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_access_event.id',
        name='corporate_access_event_agenda_corporate_access_event_id_fkey',
        ondelete='CASCADE'), nullable=False)

    title = db.Column(db.String(128))  # day of agenda
    secondary_title = db.Column(db.String(128))  # title of agenda
    started_at = db.Column(db.DateTime)
    ended_at = db.Column(db.DateTime)
    description = db.Column(db.String(512))
    address = db.Column(db.String(256))

    # relationships
    corporate_access_event = db.relationship(
        'CorporateAccessEvent', backref=db.backref(
            'agendas', lazy='dynamic', passive_deletes=True,
            order_by='CorporateAccessEventAgenda.started_at'))

    def __init__(self, created_by=None, updated_by=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        super(CorporateAccessEventAgenda, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CorporateAccessEventAgenda %r>' % (self.row_id)
