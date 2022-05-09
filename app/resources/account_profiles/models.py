"""
Models for "account profiles" package.
"""

import os

from flask import current_app

from app import db
from app.common.utils import get_s3_download_link, do_nothing
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString
from app.resources.account_profiles import constants as ACCT_PROFILE
from app.resources.accounts import constants as ACCOUNT
from app.resources.sectors.models import Sector
from app.resources.industries.models import Industry


class AccountProfile(BaseModel):

    __tablename__ = 'account_profile'

    root_profile_photo_folder_key = 'ACCT_PROFILE_PHOTO_FOLDER'
    root_cover_photo_folder_key = 'ACCT_COVER_PHOTO_FOLDER'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='account_profile_account_id_fkey',
        ondelete='CASCADE'), nullable=False)
    account_type = db.Column(ChoiceString(ACCOUNT.ACCT_TYPES_CHOICES),
                             nullable=False)

    description = db.Column(db.String(9216))
    # mainly corporate/company type related data
    sector_id = db.Column(db.BigInteger, db.ForeignKey(
        'sector.id', name='account_profile_sector_id_fkey'))
    industry_id = db.Column(db.BigInteger, db.ForeignKey(
        'industry.id', name='account_profile_industry_id_fkey'))
    region = db.Column(db.String(128))
    country = db.Column(db.String(128))
    market_cap = db.Column(db.BigInteger)
    stock_price = db.Column(db.String(128))
    shares = db.Column(db.String(128))
    # mainly institution related data
    institution_type = db.Column(db.String(256))
    institution_style = db.Column(db.String(256))
    cap_group = db.Column(ChoiceString(ACCT_PROFILE.CAP_TYPES_CHOICES))
    number_of_holdings = db.Column(db.Integer)
    top_ten_holdings_percentage = db.Column(db.Numeric(5, 2), default=0)
    currency = db.Column(db.String(32))

    # common?
    turnover = db.Column(db.String(256))
    profile_photo = db.Column(db.String())
    cover_photo = db.Column(db.String())
    profile_thumbnail = db.Column(db.String())
    cover_thumbnail = db.Column(db.String())

    # address
    address_street_one = db.Column(db.String(256))
    address_street_two = db.Column(db.String(256))
    address_city = db.Column(db.String(128))
    address_state = db.Column(db.String(128))
    address_zip_code = db.Column(db.String(128))
    address_country = db.Column(db.String(128))
    # phone numbers
    phone_primary = db.Column(db.String(32))
    phone_secondary = db.Column(db.String(32))
    phone_alternate = db.Column(db.String(32))
    # deleted bit
    deleted = db.Column(db.Boolean, default=False)

    # one-to-one relationship, hence uselist is False
    account = db.relationship('Account', backref=db.backref(
        'profile', uselist=False, passive_deletes=True))
    sector = db.relationship('Sector', backref=db.backref(
        'account_profiles', lazy='dynamic'))
    industry = db.relationship('Industry', backref=db.backref(
        'account_profiles', lazy='dynamic'))
    child_accounts = db.relationship(
        'Account', backref=db.backref(
            'child_account_profile', uselist=False),
        foreign_keys='[Account.parent_account_id]',
        primaryjoin="AccountProfile.account_id == Account.parent_account_id",
        viewonly=True)

    # dynamic properties
    profile_photo_url = None
    cover_photo_url = None
    profile_thumbnail_url = None
    cover_thumbnail_url = None

    def __init__(self, created_by=None, updated_by=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        super(AccountProfile, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<AccountProfile %r>' % (self.row_id)

    def load_urls(self, with_redirect=False, expires_in=15552000,
                  thumbnail_only=False):
        """
        Populates the profile_photo_url, cover_photo_url,
        profile_thumbnail_url and cover_thumbnail_url dynamic properties
        (For photo s3 url will expire after 180 days)
        """
        s3_url = ''
        thumbnail_bucket_name = ''
        if (not self.profile_photo and not self.cover_photo and
                not self.profile_thumbnail and not self.cover_thumbnail):
            return
        sub_folder = self.file_subfolder_name()
        if current_app.config['S3_UPLOAD']:
            if self.cover_thumbnail or self.profile_thumbnail:
                thumbnail_bucket_name = current_app.config[
                    'S3_THUMBNAIL_BUCKET']
                s3_url = 'https://s3-ap-southeast-1.amazonaws.com/'
            signer = get_s3_download_link
        else:
            signer = do_nothing
        if self.cover_thumbnail:
            self.cover_thumbnail_url = os.path.join(
                s3_url, thumbnail_bucket_name,
                current_app.config[self.root_cover_photo_folder_key],
                sub_folder, self.cover_thumbnail)
        if self.profile_thumbnail:
            self.profile_thumbnail_url = os.path.join(
                s3_url, thumbnail_bucket_name,
                current_app.config[self.root_profile_photo_folder_key],
                sub_folder, self.profile_thumbnail)
        if thumbnail_only:
            return
        if self.profile_photo:
            self.profile_photo_url = signer(os.path.join(
                current_app.config[self.root_profile_photo_folder_key],
                sub_folder, self.profile_photo), expires_in=expires_in)
        if self.cover_photo:
            self.cover_photo_url = signer(os.path.join(
                current_app.config[self.root_cover_photo_folder_key],
                sub_folder, self.cover_photo), expires_in=expires_in)
        return

    def sort_management(self):
        """
        sorting management by sequence_id
        """
        if self.management_profiles:
            self.management_profiles = sorted(
                self.management_profiles, key=lambda k: k.sequence_id)
        return
