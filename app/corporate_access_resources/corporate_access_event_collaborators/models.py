"""
Models for "corporate access event collaborators" package.
"""

from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY

from app import db
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString
from app.base import constants as APP
# related model imports done in corporate_access_resources/__init__


class CorporateAccessEventCollaborator(BaseModel):

    __tablename__ = 'corporate_access_event_collaborator'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_coll_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_coll_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)

    corporate_access_event_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_access_event.id',
        name='corporate_access_event_coll_corporate_access_event_id_fkey',
        ondelete='CASCADE'), nullable=False)
    collaborator_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_coll_collaborator_id_fkey',
        ondelete='CASCADE'), nullable=False)
    permissions = db.Column(ARRAY(db.String(256)))

    # for mail sent or not
    is_mail_sent = db.Column(db.Boolean, default=False)
    email_status = db.Column(ChoiceString(APP.EMAIL_STATUS_CHOICES),
                             nullable=False, default=APP.EMAIL_NOT_SENT)
    # relationships
    corporate_access_event = db.relationship(
        'CorporateAccessEvent', backref=db.backref(
            'collaborators', lazy='dynamic',
            passive_deletes=True))
    creator = db.relationship('User', backref=db.backref(
        'corporate_access_event_colls_created', lazy='dynamic'),
        foreign_keys='CorporateAccessEventCollaborator.created_by')
    collaborator = db.relationship('User', backref=db.backref(
        'corporate_access_events_collaboratored', lazy='dynamic'),
        foreign_keys='CorporateAccessEventCollaborator.collaborator_id')
    collaborator_j = db.relationship(
        'CorporateAccessEvent', secondary='user',
        backref=db.backref('collaborated', uselist=False),
        foreign_keys='[CorporateAccessEventCollaborator.'
        'corporate_access_event_id,'
        'CorporateAccessEventCollaborator.collaborator_id]',
        primaryjoin='CorporateAccessEvent.row_id =='
        'CorporateAccessEventCollaborator.corporate_access_event_id',
        secondaryjoin='CorporateAccessEventCollaborator.collaborator_id =='
        'User.row_id', viewonly=True)

    # multi column
    __table_args__ = (
        UniqueConstraint(
            'corporate_access_event_id', 'collaborator_id',
            name='c_corporate_access_event_id_collaborator_id_key'),
    )

    def __init__(self, created_by=None, updated_by=None,
                 corporate_access_event_id=None, collaborator_id=None,
                 *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        self.corporate_access_event_id = corporate_access_event_id
        self.collaborator_id = collaborator_id

        super(CorporateAccessEventCollaborator, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CorporateAccessEventCollaborator %r>' % (self.row_id)
