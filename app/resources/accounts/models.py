"""
Models for "accounts" package.
"""

from sqlalchemy import func, Index
from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString
from app.resources.accounts import constants as ACCOUNT
from app.domain_resources.domains.models import Domain


class Account(BaseModel):

    __tablename__ = 'account'
    __global_searchable__ = ['account_name']

    account_name = db.Column(db.String(512), nullable=False)
    account_type = db.Column(ChoiceString(ACCOUNT.ACCT_TYPES_CHOICES),
                             nullable=False)
    # grouping
    parent_account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='account_parent_account_id_fkey',
        ondelete='CASCADE'))
    domain_id = db.Column(db.BigInteger, db.ForeignKey(
        'domain.id', name='account_domain_id_fkey', ondelete='RESTRICT'),
                           nullable=False)
    is_parent = db.Column(db.Boolean, default=False)

    billing_street = db.Column(db.String(128))
    billing_city = db.Column(db.String(128))
    billing_state = db.Column(db.String(128))
    billing_code = db.Column(db.String(128))
    billing_country = db.Column(db.String(128))

    identifier = db.Column(db.String(128))
    isin_number = db.Column(db.String(128))
    sedol = db.Column(db.String(128))
    perm_security_id = db.Column(db.String(128))
    fsym_id = db.Column(db.String(128))
    nse_symbol = db.Column(db.String(32))
    bse_symbol = db.Column(db.String(32))
    # ec_identifier = db.Column(db.String(128))

    created_by = db.Column(db.BigInteger, nullable=False)
    updated_by = db.Column(db.BigInteger, nullable=False)

    # account status/access related information
    # when was the first user created for this account
    activation_date = db.Column(db.DateTime)
    # subscription period
    subscription_start_date = db.Column(db.DateTime)
    subscription_end_date = db.Column(db.DateTime)
    is_trial = db.Column(db.Boolean, default=False)  # only for display purpose
    # #TODO: add historical tracking of subscriptions, which will contain
    # all the 3 above columns

    # will be used to give access to accounts
    # if their users can download reports or not.
    is_download_report = db.Column(db.Boolean, default=False)
    # will be used to give access to accounts
    # if their users can use export excel functionality or not.
    export_enabled = db.Column(db.Boolean, default=False)

    # deleted bit
    deleted = db.Column(db.Boolean, default=False)
    blocked = db.Column(db.Boolean, default=False)

    # keywords for getting news
    keywords = db.Column(db.ARRAY(db.String()), default=[])
    is_sme = db.Column(db.Boolean, default=False)
    facebook_id = db.Column(db.String(512))
    twitter_id = db.Column(db.String(512))
    linkedin_id = db.Column(db.String(512))
    website = db.Column(db.String(512))

    # table add unique account name every time
    # combine unique key
    __table_args__ = (
        # unique lower case index, i.e case-insensitive unique constraint
        # Index('account_is_not_deleted_unique', func.lower(account_name), deleted,
        #       unique=True),
        # Index('identifier_not_deleted_unique', identifier, deleted,
        #       unique=True),
        Index('ci_account_unique_account_name', func.lower(account_name),
              unique=True),
    )

    child_accounts = db.relationship('Account', backref=db.backref(
        'parent_accounts', remote_side='Account.row_id'))
    domain = db.relationship('Domain', backref=db.backref(
        'accounts', uselist=True),
        primaryjoin='Account.domain_id == Domain.row_id')

    # dynamic properties
    is_account_active = None

    def __init__(self, account_name=None, created_by=None, updated_by=None,
                 *args, **kwargs):
        self.account_name = account_name
        self.created_by = created_by
        self.updated_by = updated_by
        super(Account, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Account %r>' % (self.account_name)

    def load_is_account_active(self):
        """
        checking whether account has activation_date or not then
        change is_account_active status accordingly
        """
        if self.activation_date:
            self.is_account_active = True
        else:
            self.is_account_active = False
        return


class AccountPeerGroup(BaseModel):
    __tablename__ = 'account_peer_group'

    primary_account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='peer_primary_account_id_fkey',
        ondelete='CASCADE'))

    peer_account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='peer_account_id_fkey',
        ondelete='CASCADE'))

    created_by = db.Column(db.BigInteger, nullable=False)
    updated_by = db.Column(db.BigInteger, nullable=False)

    primary_account = db.relationship('Account', backref=db.backref(
        'peer_groups', lazy='dynamic'),
        foreign_keys='AccountPeerGroup.primary_account_id')
    peer_account = db.relationship('Account', backref=db.backref(
        'peer_accounts_j', lazy='dynamic'),
        foreign_keys='AccountPeerGroup.peer_account_id')

    # multi column
    __table_args__ = (
        UniqueConstraint('primary_account_id', 'peer_account_id',
                         name='c_primary_account_id_peer_account_id_key'),
    )

    def __init__(self, primary_account_id=None, *args, **kwargs):
        self.primary_account_id = primary_account_id
        super(AccountPeerGroup, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<AccountPeerGroup %r>' % (self.primary_account_id)