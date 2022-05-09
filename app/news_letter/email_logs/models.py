"""
Models for "distribution list of user" package.
"""

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString
from app.base.model_fields import ChoiceString
from app.news_letter.email_logs import constants as CHOICE
from app.resources.users.models import User
from app.news_letter.distribution_list.models import DistributionList

# related model imports done in toolkit/__init__


class Emaillogs(BaseModel):

    __tablename__ = 'email_logs'

    email_sent = db.Column(ChoiceString(CHOICE.ACTIONS),
                             nullable=False)
    # user_email = db.Column(LCString(128), nullable=False)
    user_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='emaillog_user_id_fkey', 
        ondelete='CASCADE'))
    dist_user_id = db.Column(db.BigInteger, db.ForeignKey(
        'distribution_list.id', name='emaillog_dist_user_id_fkey', 
        ondelete='CASCADE'))
    domain_id = db.Column(db.BigInteger, db.ForeignKey(
        'domain.id', name='email_logs_domain_id_fkey'), nullable=False)

    user = db.relationship('User', backref=db.backref(
        'emaillog_user', lazy='dynamic'), foreign_keys='Emaillogs.user_id')
    dict_user = db.relationship('DistributionList', backref=db.backref(
        'emaillog_dist_user', lazy='dynamic'), foreign_keys='Emaillogs.dist_user_id')
    domain = db.relationship('Domain', backref=db.backref(
        'email_logs_domain', lazy='dynamic'),
    foreign_keys='Emaillogs.domain_id')

    def __init__(self, *args, **kwargs):
        super(Emaillogs, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Emaillogs %r>' % (self.row_id)
