"""
Models for "account settings" package.
"""

from sqlalchemy.dialects.postgresql import JSONB

from app import db
from app.base.models import BaseModel


class AccountSettings(BaseModel):

    __tablename__ = 'account_settings'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='account_settings_account_id_fkey',
        ondelete='CASCADE'), unique=True, nullable=False)

    event_sender_email = db.Column(db.String(256), unique=True)
    event_sender_name = db.Column(db.String(256))
    # #TODO: if ever required in the future
    # event_sender_domain = db.Column(db.String(256))
    # event_sender_domain_token = db.Column(db.String(256))

    # if email/domain is verified or not (with sending service)
    event_sender_verified = db.Column(db.Boolean, default=False)
    # if domain of the sending email/domain is verified or not (
    # with SPF and/or DKIM)
    event_sender_domain_verified = db.Column(db.Boolean, default=False)
    # extra fields from vendor specific api calls
    ses_email_verification_response = db.Column(JSONB)
    ses_email_verification_status_response = db.Column(JSONB)

    # deleted bit
    deleted = db.Column(db.Boolean, default=False)

    # relationships
    account = db.relationship('Account', backref=db.backref(
        'settings', uselist=False, passive_deletes=True),
        primaryjoin='Account.row_id == AccountSettings.account_id')

    # dynamic properties
    verfied_status = False

    def __init__(self, account_id=None, *args, **kwargs):
        self.account_id = account_id
        super(AccountSettings, self).__init__(*args, **kwargs)

    @db.reconstructor
    def init_on_load(self):
        """
        initialise some dynamic properties and extras.
        """
        self.load_verified_status()

    def __repr__(self):
        return '<AccountSettings %r>' % (self.account_id)

    def load_verified_status(self):
        """
        Calculates the actual verified status, i.e 'and' of
        event_sender_verified and event_sender_domain_verified
        """
        self.verified_status =\
            self.event_sender_verified and self.event_sender_domain_verified
