"""
Models for "admin publish notifications" package.
"""

from app import db
from app.base.model_fields import ChoiceString
from app.base.models import BaseModel
from app.resources.accounts import constants as ACCOUNT


class AdminPublishNotification(BaseModel):

    __tablename__ = 'admin_publish_notification'

    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(2048))
    account_type_preference = db.Column(db.ARRAY(
        ChoiceString(ACCOUNT.ACCT_TYPES_CHOICES)))

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='admin_publish_notification_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='admin_publish_notification_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)
    domain_id = db.Column(db.BigInteger, db.ForeignKey(
        'domain.id', name='admin_publish_notification_domain_id_fkey',
        ondelete='RESTRICT'), nullable=False)

    creator = db.relationship('User', backref=db.backref(
        'admin_publish_notifications', lazy='dynamic'),
        foreign_keys='AdminPublishNotification.created_by')

    def __init__(self, title=None, created_by=None, updated_by=None,
                 *args, **kwargs):
        self.title = title
        self.created_by = created_by
        self.updated_by = updated_by
        super(AdminPublishNotification, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<AdminPublishNotification %r>' % (self.title)
