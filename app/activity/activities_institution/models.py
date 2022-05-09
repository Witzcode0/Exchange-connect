"""
Models for "activity institution" package.
"""

from sqlalchemy import CheckConstraint, UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString, ChoiceString


class ActivityInstitution(BaseModel):

    __tablename__ = 'activity_institution'

    activity_id = db.Column(db.BigInteger, db.ForeignKey(
        'activity.id', name='institute_activity_id_fkey', ondelete="CASCADE"), 
    nullable=False)

    account_name = db.Column(db.String(256))

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='institute_account_id_fkey', ondelete='CASCADE'))

    factset_entity_id = db.Column(db.String(256))

    account = db.relationship('Account', backref=db.backref(
        'institution_account', lazy='dynamic'), foreign_keys='ActivityInstitution.account_id')

    # activity = db.relationship('Activity', backref=db.backref(
    #     'activity_institution_activity', uselist=True),
    #     primaryjoin='ActivityInstitution.activity_id == Activity.row_id')

    def __init__(self, *args, **kwargs):
        super(ActivityInstitution, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<ActivityInstitution %r>' % (self.account_name)


class ActivityInstitutionParticipant(BaseModel):

    __tablename__ = 'activity_institution_participant'

    activity_id = db.Column(db.BigInteger, db.ForeignKey(
        'activity.id', name='institute_participant_activity_id_fkey', ondelete="CASCADE"), 
    nullable=False)

    participant_name = db.Column(db.String(256))

    user_id = db.Column(db.BigInteger, db.ForeignKey(
        'user_profile.id', name='institution_participant_user_id_fkey', ondelete='CASCADE'))

    contact_id = db.Column(db.Integer, db.ForeignKey(
        'crm_contact.id', name='institution_contact_id_fkey', ondelete='CASCADE'))

    people_id = db.Column(db.String(256))

    users = db.relationship('UserProfile', backref=db.backref(
        'institution_participant_users', lazy='dynamic'), 
    foreign_keys='ActivityInstitutionParticipant.user_id')

    contacts = db.relationship('CRMContact', backref=db.backref(
        'institution_contacts', lazy='dynamic'), 
    foreign_keys='ActivityInstitutionParticipant.contact_id')

    # activity = db.relationship('Activity', backref=db.backref(
    #     'activity_institution_activity', uselist=True),
    #     primaryjoin='ActivityInstitution.activity_id == Activity.row_id')

    def __init__(self, account_name=None, participant_name=None, user_id=None, contact_id=None, people_id=None, *args, **kwargs):
        self.activity_id = account_name
        self.participant_name = participant_name
        self.user_id = user_id
        self.people_id = people_id
        self.contact_id = contact_id
        super(ActivityInstitutionParticipant, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<ActivityInstitutionParticipant %r>' % (self.row_id)