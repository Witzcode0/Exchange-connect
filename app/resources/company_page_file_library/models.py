"""
Models for "company page file library" package.
"""

import os

from flask import current_app

from app import db
from app.base.models import BaseModel


class CompanyPageLibraryFile(BaseModel):
    """
    Files will always be public
    """

    __tablename__ = 'company_page_library_file'
    # config key for root folder of files
    root_folder_key = 'COMPANY_PAGE_FILE_FOLDER'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='company_page_library_file_account_id_fkey',
        ondelete='CASCADE'), nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='company_page_library_file_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='company_page_library_file_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)

    filename = db.Column(db.String())
    file_type = db.Column(db.String(256))
    thumbnail_name = db.Column(db.String())

    # deleted bit
    deleted = db.Column(db.Boolean, default=False)

    account = db.relationship('Account', backref=db.backref(
        'companypagefiles', lazy='dynamic'))
    creator = db.relationship(
        'User', backref=db.backref('companypagefiles', lazy='dynamic'),
        foreign_keys='CompanyPageLibraryFile.created_by')

    # dynamic properties
    file_url = None
    thumbnail_url = None

    def __init__(self, created_by=None, updated_by=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        super(CompanyPageLibraryFile, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CompanyPageLibraryFile %r>' % (self.row_id)

    def load_urls(self, with_redirect=False, expires_in=3600,
                  thumbnail_only=False):
        """
        Populates the photo_urls, video_url, audio_url and other_file_url
        dynamic properties
        """
        s3_url = ''
        thumbnail_bucket_name = ''
        if not self.filename and not self.thumbnail_name:
            return
        sub_folder = self.file_subfolder_name()
        if current_app.config['S3_UPLOAD']:
            if self.thumbnail_name:
                thumbnail_bucket_name = current_app.config[
                    'S3_THUMBNAIL_BUCKET']
            s3_url = 'https://s3-ap-southeast-1.amazonaws.com/'
            bucket_name = current_app.config['S3_BUCKET']
        else:
            bucket_name = current_app.config['BASE_UPLOADS_FOLDER']
        if self.thumbnail_name:
            self.thumbnail_url = os.path.join(
                s3_url, thumbnail_bucket_name,
                current_app.config[self.root_folder_key],
                sub_folder, self.thumbnail_name)
        if thumbnail_only:
            return
        if self.filename:
            self.file_url = os.path.join(
                s3_url, bucket_name, current_app.config[self.root_folder_key],
                sub_folder, self.filename)
        return
