"""
Models for "crm file library" package.
"""

import os

from flask import current_app

from app import db
from app.common.utils import get_s3_download_link, do_nothing
from app.base.models import BaseModel


class CRMDistributionLibraryFile(BaseModel):

    __tablename__ = 'crm_distribution_library_file'
    # config key for root folder of files
    root_folder_key = 'CRM_DIST_LIBRARY_FILE_FOLDER'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='crm_dist_library_file_account_id_fkey',
        ondelete='CASCADE'), nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='crm_dist_library_file_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='crm_dist_library_file_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)

    filename = db.Column(db.String())
    file_type = db.Column(db.String(256))

    account = db.relationship('Account', backref=db.backref(
        'crmdistlibraryfiles', lazy='dynamic'))
    creator = db.relationship(
        'User', backref=db.backref('crmdistlibraryfiles', lazy='dynamic'),
        foreign_keys='CRMDistributionLibraryFile.created_by')

    # dynamic properties
    file_url = None

    def __init__(self, created_by=None, updated_by=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        super(CRMDistributionLibraryFile, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CRMDistributionLibraryFile %r>' % (self.row_id)

    def load_urls(self, with_redirect=False):
        """
        Populates the photo_urls, video_url, audio_url and other_file_url
        dynamic properties
        """
        s3_url = ''
        thumbnail_bucket_name = ''
        if not self.filename:
            return
        sub_folder = self.file_subfolder_name()
        if current_app.config['S3_UPLOAD']:
            thumbnail_bucket_name = current_app.config[
                'S3_THUMBNAIL_BUCKET']
            s3_url = 'https://s3-ap-southeast-1.amazonaws.com/'
        if self.filename:
            self.file_url = os.path.join(
                s3_url, thumbnail_bucket_name,
                current_app.config[self.root_folder_key],
                sub_folder, self.filename)
        return
