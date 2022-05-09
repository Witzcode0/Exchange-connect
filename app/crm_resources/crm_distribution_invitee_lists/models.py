"""
Models for "crm distribution invitee list" package.
"""

from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString, ChoiceString
from app.base import constants as APP
from app.crm_resources.crm_distribution_lists.models import CRMDistributionList


class CRMDistributionInviteeList(BaseModel):

    __tablename__ = 'crm_distribution_invitee_list'

    created_by = db.Column(db.Integer, db.ForeignKey('user.id'),
                           nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'),
                           nullable=False)

    distribution_list_id = db.Column(db.BigInteger, db.ForeignKey(
        'crm_distribution_list.id',
        name='dist_invitee_crm_distribution_list_id_fkey', ondelete='CASCADE'),
        nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    invitee_email = db.Column(LCString(128), nullable=False)
    # if email is provided, then first_name and last_name is expected
    # (not required)
    invitee_first_name = db.Column(db.String(128), nullable=False)
    invitee_last_name = db.Column(db.String(128))

    # for mail sent or not
    is_mail_sent = db.Column(db.Boolean, default=False)
    email_status = db.Column(ChoiceString(APP.EMAIL_STATUS_CHOICES),
                             nullable=False, default=APP.EMAIL_NOT_SENT)
    sent_on = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            'distribution_list_id', 'invitee_email',
            name='c_distribution_list_id_invitee_email_key'),
    )

    # relationships
    crm_distribution_list = db.relationship(
        'CRMDistributionList', backref=db.backref(
            'crm_distribution_invitees', lazy='dynamic',
            passive_deletes=True))

    user = db.relationship('User', backref=db.backref(
        'dist_users', lazy='dynamic'),
        foreign_keys='CRMDistributionInviteeList.user_id')

    def __init__(self, invitee_name=None, created_by=None, *args, **kwargs):
        self.invitee_name = invitee_name
        self.created_by = created_by
        super(CRMDistributionInviteeList, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CRMDistributionInviteeList %r>' % (self.invitee_name)
