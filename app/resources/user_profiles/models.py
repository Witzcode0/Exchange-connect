"""
Models for "user profiles" package.
"""

import os
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from flask import current_app

from app import db
from app.common.utils import get_s3_download_link, do_nothing
from app.base.models import BaseModel
from app.base.model_fields import CastingArray, ChoiceString
from app.resources.accounts import constants as ACCOUNT
from app.resources.users.models import User
from app.resources.designations.models import Designation
# ^ above both required for relationships


class UserProfile(BaseModel):

    __tablename__ = 'user_profile'
    __global_searchable__ = ['user_id', 'first_name', 'last_name',
                             'designation']
    root_profile_photo_folder_key = 'USR_PROFILE_PHOTO_FOLDER'
    root_cover_photo_folder_key = 'USR_COVER_PHOTO_FOLDER'

    user_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='user_profile_user_id_fkey', ondelete='CASCADE'),
        nullable=False)
    account_type = db.Column(ChoiceString(ACCOUNT.ACCT_TYPES_CHOICES),
                             nullable=False)
    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='user_profile_account_id_fkey', ondelete='CASCADE'),
        nullable=False)
    first_name = db.Column(db.String(128), nullable=False)
    last_name = db.Column(db.String(128), nullable=False)
    company = db.Column(db.String(256))
    designation = db.Column(db.String(128))
    phone_number = db.Column(db.String(50))
    fax = db.Column(db.String(32))
    about = db.Column(db.String(9216))
    profile_photo = db.Column(db.String())
    cover_photo = db.Column(db.String())
    profile_thumbnail = db.Column(db.String())
    cover_thumbnail = db.Column(db.String())
    address_street_one = db.Column(db.String(256))
    address_street_two = db.Column(db.String(256))
    address_city = db.Column(db.String(128))
    address_state = db.Column(db.String(128))
    address_zip_code = db.Column(db.String(128))
    address_country = db.Column(db.String(128))
    experience = db.Column(CastingArray(JSONB))  # **format control in schema
    education = db.Column(CastingArray(JSONB))  # **format control in schema
    skills = db.Column(ARRAY(db.String(256)))
    interests = db.Column(ARRAY(db.String(256)))
    sector_ids = db.Column(ARRAY(db.BigInteger()))
    industry_ids = db.Column(ARRAY(db.BigInteger()))

    # #TODO: check if this is required
    deleted = db.Column(db.Boolean, default=False)

    # one-to-one relationship, hence uselist is False
    user = db.relationship('User', backref=db.backref(
        'profile', uselist=False),
        primaryjoin='UserProfile.user_id == User.row_id')
    designation_link = db.relationship(
        'Designation',
        primaryjoin='foreign(UserProfile.designation) == Designation.name',)
    account = db.relationship('Account', backref=db.backref(
        'user_profiles', lazy='dynamic'))

    # dynamic properties
    profile_photo_url = None
    cover_photo_url = None
    profile_thumbnail_url = None
    cover_thumbnail_url = None

    def __init__(self, user_id=None, first_name=None, last_name=None,
                 *args, **kwargs):
        self.user_id = user_id
        self.first_name = first_name
        self.last_name = last_name
        super(UserProfile, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<UserProfile %r>' % (self.row_id)

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
