"""
Models for "management profiles" package.
"""

import os

from flask import current_app
from sqlalchemy import UniqueConstraint

from app import db
from app.common.utils import get_s3_download_link, do_nothing
from app.base.models import BaseModel
from app.base.model_fields import LCString
from app.resources.account_profiles.models import AccountProfile
# ^required for relationship


class ManagementProfile(BaseModel):

    __tablename__ = 'management_profile'

    root_profile_photo_folder_key = 'MGMT_PROFILE_PHOTO_FOLDER'

    account_profile_id = db.Column(db.BigInteger, db.ForeignKey(
        'account_profile.id',
        name='management_profile_account_profile_id_fkey', ondelete='CASCADE'),
        nullable=False)

    # incase already existing user
    user_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='management_profile_user_id_fkey', ondelete='CASCADE'))

    # incase outside user
    name = db.Column(db.String(256))
    designation = db.Column(db.String(128))
    description = db.Column(db.String(9216))
    profile_photo = db.Column(db.String())
    profile_thumbnail = db.Column(db.String())
    email = db.Column(LCString(128))

    # used for sorting the management profiles
    sequence_id = db.Column(db.Integer, nullable=False)

    # relationships
    account_profile = db.relationship('AccountProfile', backref=db.backref(
        'management_profiles'))

    # dynamic properties
    profile_photo_url = None
    profile_thumbnail_url = None

    # multi column
    __table_args__ = (
        UniqueConstraint(
            'account_profile_id', 'user_id',
            name='c_acc_profile_id_user_id_key'),
    )

    def __init__(self, *args, **kwargs):
        super(ManagementProfile, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<ManagementProfile %r>' % (self.row_id)

    def load_urls(self, with_redirect=False, expires_in=3600):
        """
        Populates the profile_photo_url dynamic properties
        """
        s3_url = ''
        thumbnail_bucket_name = ''
        if not self.profile_photo and not self.profile_thumbnail :
            return
        sub_folder = self.file_subfolder_name()
        if current_app.config['S3_UPLOAD']:
            signer = get_s3_download_link
            s3_url = 'https://s3-ap-southeast-1.amazonaws.com/'
            thumbnail_bucket_name = current_app.config[
                'S3_THUMBNAIL_BUCKET']
        else:
            signer = do_nothing
        if self.profile_photo:
            self.profile_photo_url = signer(os.path.join(
                current_app.config[self.root_profile_photo_folder_key],
                sub_folder, self.profile_photo), expires_in=expires_in)
        if self.profile_thumbnail:
            self.profile_thumbnail_url = os.path.join(
                s3_url, thumbnail_bucket_name,
                current_app.config[self.root_profile_photo_folder_key],
                sub_folder, self.profile_thumbnail)
        return
