"""
Models for "emails" package.
"""

import base64

from cryptography.fernet import Fernet

from app import db
from app.common.utils import send_email
from app.base.models import BaseModel
from app.base.model_fields import LCString
from app.common.utils import (
    create_encryption_decryption_key)
from config import BRAND_NAME


class EmailCredential(BaseModel):
    """
    Stores the email credentials
    """
    __tablename__ = 'emailcredential'

    created_by = db.Column(db.Integer, db.ForeignKey(
        'user.id', name='emailcredential_created_by_fkey'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey(
        'account.id', name='emailcredential_account_id_fkey'), nullable=False)

    name = db.Column(db.String(256), nullable=False)
    smtp_username = db.Column(db.String(256))
    smtp_password = db.Column(db.String(256))
    smtp_host = db.Column(db.String(128))
    smtp_port = db.Column(db.Integer)
    is_ssl = db.Column(db.Boolean, default=False)
    is_smtp_active = db.Column(db.Boolean, default=False)
    from_email = db.Column(LCString(128), nullable=False)

    # incase of oauth
    auth_token = db.Column(db.String())

    # relationships
    user = db.relationship(
        'User', backref=db.backref('smtp_creds', uselist=False))

    def __init__(self, created_by=None, account_id=None, smtp_username=None,
                 password=None, smtp_url=None, *args, **kwargs):
        self.created_by = created_by
        self.account_id = account_id
        self.smtp_username = smtp_username
        self.smtp_url = smtp_url
        super(EmailCredential, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<EmailCredential %r>' % (self.smtp_username)

    def encrypt_password(self, password):
        password = base64.b64decode(password).decode('utf-8')
        password = password.encode()
        key = create_encryption_decryption_key()
        f = Fernet(key)
        self.smtp_password = f.encrypt(password).decode('utf-8')

    def decrypt_password(self):
        password = self.smtp_password.encode('utf-8')
        key = create_encryption_decryption_key()
        f = Fernet(key)

        return f.decrypt(password).decode('utf-8')

    def send_test_mail(self):
        """
        When user set smtp settings test mail send to user by own mail id
        :return:
        """
        subject = '{} - User smtp setting'.format(BRAND_NAME)
        body = 'Hi %(user_name)s,\r\n\r\n' + \
               'Your smtp settings has successful.'

        body = body % {'user_name': self.user.profile.first_name}
        send_email(
            self.smtp_username, self.decrypt_password(), self.smtp_host,
            from_name=self.name, from_email=self.from_email,
            to_addresses=[self.from_email], body=body, subject=subject,
            port=self.smtp_port)

    def get_smtp_settings(self):
        if not self.is_smtp_active:
            return {}
        return {'from_name': self.name, 'from_email': self.from_email,
                'username': self.smtp_username,
                'password': self.decrypt_password(),
                'smtphost': self.smtp_host, 'port': self.smtp_port,
                'is_ssl': self.is_ssl}
