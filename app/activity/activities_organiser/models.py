"""
Models for "activity institution" package.
"""

from sqlalchemy import CheckConstraint, UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString, ChoiceString


class ActivityOrganiser(BaseModel):

    __tablename__ = 'activity_organiser'

    activity_id = db.Column(db.BigInteger, db.ForeignKey(
        'activity.id', name='organiser_activity_id_fkey', ondelete="CASCADE"), nullable=False)

    account_name = db.Column(db.String(256))

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='organiser_account_id_fkey', ondelete='CASCADE'))

    account = db.relationship('Account', backref=db.backref(
        'organiser_account', lazy='dynamic'), foreign_keys='ActivityOrganiser.account_id')

    # activity = db.relationship('Activity', backref=db.backref(
    #     'activity_institution_activity', uselist=True),
    #     primaryjoin='ActivityInstitution.activity_id == Activity.row_id')

    def __init__(self, *args, **kwargs):
        super(ActivityOrganiser, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<ActivityOrganiser %r>' % (self.account_name)

class ActivityOrganiserParticipant(BaseModel):

    __tablename__ = 'activity_organiser_participant'

    activity_id = db.Column(db.BigInteger, db.ForeignKey(
        'activity.id', name='organiser_participant_activity_id_fkey', ondelete="CASCADE"), nullable=False)

    participant_name = db.Column(db.String(256))

    user_id = db.Column(db.BigInteger, db.ForeignKey(
        'user_profile.id', name='organiser_participant_user_id_fkey', ondelete='CASCADE'))

    contact_id = db.Column(db.Integer, db.ForeignKey(
        'crm_contact.id', name='organiser_contact_d_fkey', ondelete='CASCADE'))

    users = db.relationship('UserProfile', backref=db.backref(
        'organiser_participant_users', lazy='dynamic'), 
    foreign_keys='ActivityOrganiserParticipant.user_id')

    contacts = db.relationship('CRMContact', backref=db.backref(
        'organiser_contacts', lazy='dynamic'), 
    foreign_keys='ActivityOrganiserParticipant.contact_id')

    # activity = db.relationship('Activity', backref=db.backref(
    #     'activity_institution_activity', uselist=True),
    #     primaryjoin='ActivityInstitution.activity_id == Activity.row_id')

    def __init__(self, *args, **kwargs):
        super(ActivityOrganiserParticipant, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<ActivityOrganiserParticipant %r>' % (self.participant_name)