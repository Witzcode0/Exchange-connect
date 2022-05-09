"""
Models for "activity institution" package.
"""

from sqlalchemy import CheckConstraint, UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString, ChoiceString


class ActivityRepresentative(BaseModel):

    __tablename__ = 'activity_representative'

    activity_id = db.Column(db.BigInteger, db.ForeignKey(
        'activity.id', name='representative_activity_id_fkey', ondelete="CASCADE"), nullable=False)

    user_id = db.Column(db.BigInteger, db.ForeignKey(
        'user_profile.id', name='representative_user_id_fkey', ondelete='CASCADE'))

    contact_id = db.Column(db.Integer, db.ForeignKey(
        'crm_contact.id', name='representative_contact_d_fkey', ondelete='CASCADE'))

    user_name = db.Column(db.String(256))

    users = db.relationship('UserProfile', backref=db.backref(
        'representation_users', lazy='dynamic'), 
    foreign_keys='ActivityRepresentative.user_id')

    contacts = db.relationship('CRMContact', backref=db.backref(
        'representation_contacts', lazy='dynamic'), 
    foreign_keys='ActivityRepresentative.contact_id')

    # activity = db.relationship('Activity', backref=db.backref(
    #     'activity_institution_activity', uselist=True),
    #     primaryjoin='ActivityInstitution.activity_id == Activity.row_id')

    def __init__(self, *args, **kwargs):
        super(ActivityRepresentative, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<ActivityRepresentative %r>' % (self.user_name)