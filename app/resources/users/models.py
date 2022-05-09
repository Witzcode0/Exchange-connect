"""
Models for "user" package.
"""

import random
import string
import hashlib
import hmac

from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString, ChoiceString
from app.resources.users import constants as USER
from app.resources.accounts import constants as ACCOUNT
from app.resources.roles.models import Role
from app.resources.accounts.models import Account
from app.resources.unsubscriptions.models import Unsubscription

from socketapp.base import constants as SOCKETAPP


class User(BaseModel):

    __tablename__ = 'user'
    __global_searchable__ = ['email']

    email = db.Column(LCString(128), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

    # these will not be fk, as the default is created with command
    created_by = db.Column(db.BigInteger, nullable=False)
    updated_by = db.Column(db.BigInteger, nullable=False)

    role_id = db.Column(db.BigInteger, db.ForeignKey(
        'role.id', name='user_role_id_fkey', ondelete='CASCADE'))
    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='user_account_id_fkey', ondelete='CASCADE'),
        nullable=False)
    account_type = db.Column(ChoiceString(ACCOUNT.ACCT_TYPES_CHOICES),
                             nullable=False)

    # used for sorting the users
    sequence_id = db.Column(db.Integer, nullable=False)

    # on first visit user will be asked to change password
    f_password_updated = db.Column(db.Boolean, default=False)
    # on first visit user will also be required to update profile
    f_profile_updated = db.Column(db.Boolean, default=False)

    # to be used in combination with jwt token, if this is True alongwith
    # a valid token, then all is good, else 401
    token_valid = db.Column(db.Boolean, default=False)
    token_valid_mobile = db.Column(db.Boolean, default=False)
    token_key = db.Column(db.String(128))

    deleted = db.Column(db.Boolean, default=False)
    deactivated = db.Column(db.Boolean, default=False)
    # for email verification
    unverified = db.Column(db.Boolean, default=False)
    # for admin of company
    is_admin = db.Column(db.Boolean, default=False)
    # terms and conditions
    accepted_terms = db.Column(db.Boolean, default=False)

    # unsuccessful logins
    unsuccessful_login_count = db.Column(db.Integer, default=0)
    # last login
    last_login = db.Column(db.DateTime)
    last_logout = db.Column(db.DateTime)
    # password history
    # password_history = db.Column()

    # for stats
    total_files = db.Column(db.BigInteger, default=0)
    total_videos = db.Column(db.BigInteger, default=0)
    total_companies = db.Column(db.BigInteger, default=0)
    total_contacts = db.Column(db.BigInteger, default=0)
    # current notification count
    current_notification_count = db.Column(db.BigInteger, default=0) # for exchangeconnect
    current_notification_designlab_count = db.Column(db.BigInteger, default=0) # for designlab

    # for registration request
    is_registration_request = db.Column(db.Boolean, default=False)
    role = db.relationship('Role', backref=db.backref(
        'users', lazy='dynamic'), foreign_keys='User.role_id')
    account = db.relationship('Account', backref=db.backref(
        'users', lazy='dynamic'), foreign_keys='User.account_id')
    unsubscriptions = db.relationship('Unsubscription',  backref=db.backref(
        'users', lazy='dynamic'), foreign_keys='User.email',
         primaryjoin="Unsubscription.email == User.email", viewonly=True)
    # for crm contact identification
    is_crm_contact = db.Column(db.Boolean, default=False)
    report_download_limit = db.Column(db.Integer, default=0)
    report_downloaded = db.Column(db.Integer, default=0)

    # from design lab identification
    only_design_lab = db.Column(db.Boolean, default=False)
    # know if the verification mail is sent
    verify_mail_sent = db.Column(db.Boolean, default=False)

    # dynamic properties
    login_locked = None

    def __init__(self, email=None, password=None, first_name=None,
                 last_name=None, created_by=None, updated_by=None,
                 *args, **kwargs):
        self.email = email
        self.set_password(password)
        self.first_name = first_name
        self.last_name = last_name
        self.created_by = created_by
        self.updated_by = updated_by
        super(User, self).__init__(*args, **kwargs)

    @db.reconstructor
    def init_on_load(self):
        """
        when querying model using sqlalchemy init does not get called
        so to set variable values or function calling we created this function
        with reconstructor decoder.
        """
        self.load_login_locked()

    def __repr__(self):
        return '<User %r>' % (self.email)

    def auto_generate_password(self):
        """
        During first addition of user, the password is generated for the user
        **note: currently unused
        """
        password = ''.join(random.SystemRandom().choice(
            string.ascii_uppercase + string.digits)
            for _ in range(USER.AUTO_PASSWORD_LENGTH))
        self.set_password(password)
        return password

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def load_login_locked(self):
        """
        by checking unsuccessful login count then change login_locked
        status accordingly
        """
        if (self.unsuccessful_login_count and
                self.unsuccessful_login_count >= USER.MAX_UNSUCCESSFUL_LOGINS):
            self.login_locked = True
        else:
            self.login_locked = False
        return

    def get_room_id(self, room_type=SOCKETAPP.NS_FEED):
        """
        Generate the hashed feed_room id for this user.
        row_id + email + /feed

        :param room_type:
            the namespace for which to create the room id
        """
        if room_type not in [SOCKETAPP.NS_FEED, SOCKETAPP.NS_NOTIFICATION,
        SOCKETAPP.NS_DESIGNLAB_NOTIFICATION]:
            raise Exception('Unknown room type')
        message = str(self.row_id) + self.email + room_type
        result = hmac.new(bytes(current_app.config['SECRET_KEY'], 'ascii'),
                          bytes(message, 'ascii'), hashlib.sha1).hexdigest()
        return result
