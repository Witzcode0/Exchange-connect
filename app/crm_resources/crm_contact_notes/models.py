"""
Models for "crm contact notes" package.
"""

from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString
from app.crm_resources.crm_contact_notes import constants as NOTE

# association table for many-to-many CorporateAccessEvent files
crmusernotes = db.Table(
    'crmusernotes',
    db.Column('note_id', db.BigInteger, db.ForeignKey(
        'crm_contact_note.id',
        name='crmusernotes_note_id_fkey', ondelete="CASCADE"),
        nullable=False),
    db.Column('user_id', db.BigInteger, db.ForeignKey(
        'user.id', name='crmusernotes_user_id_fkey',
        ondelete="CASCADE"), nullable=False),
    UniqueConstraint('note_id', 'user_id',
                     name='ac_note_id_user_id_key'),
)


class CRMContactNote(BaseModel):
    __tablename__ = 'crm_contact_note'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='crm_contact_note_account_id_fkey',
        ondelete='CASCADE'), nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='crm_contact_note_created_by_fkey',
        ondelete='CASCADE'), nullable=False)

    ca_event_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_access_event.id', name='crm_contact_note_ca_event_id_fkey',
        ondelete='CASCADE'))
    webinar_id = db.Column(db.BigInteger, db.ForeignKey(
        'webinar.id', name='crm_contact_note_webinar_id_fkey',
        ondelete='CASCADE'))
    webcast_id = db.Column(db.BigInteger, db.ForeignKey(
        'webcast.id', name='crm_contact_note_webcast_id_fkey',
        ondelete='CASCADE'))

    note_type = db.Column(ChoiceString(NOTE.NOTE_TYPES_CHOICES),
                          nullable=False, default=NOTE.NOTE_PRIVATE)
    title = db.Column(db.String(256))
    note = db.Column(db.String(), nullable=False)

    account = db.relationship('Account', backref=db.backref(
        'crmcontactnotes', lazy='dynamic'))
    creator = db.relationship(
        'User', backref=db.backref('crmcontactnotes', lazy='dynamic'),
        foreign_keys='CRMContactNote.created_by')
    users = db.relationship(
        'User', secondary=crmusernotes, backref=db.backref(
            'crmnotesforusers', lazy='dynamic'), passive_deletes=True)

    def __init__(self, created_by=None, updated_by=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        super(CRMContactNote, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CRMContactNote %r>' % (self.note)
