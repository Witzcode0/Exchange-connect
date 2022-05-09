"""
Models for "semi documentation parsing file" package.
"""

import os

from flask import current_app

from app import db
from app.common.utils import do_nothing
from app.base.models import BaseModel


class ParsingFile(BaseModel):

    __tablename__ = 'parsing_file'
    # config key for root folder of files
    root_folder_key = 'PARSING_FILE_FOLDER'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='parsing_file_account_id_fkey', ondelete='CASCADE'),
        nullable=False)

    file_type = db.Column(db.String(256))
    filename = db.Column(db.String())

    # deleted bit
    deleted = db.Column(db.Boolean, default=False)

    account = db.relationship('Account', backref=db.backref(
        'parsing_files', lazy='dynamic'),
                              foreign_keys='ParsingFile.account_id')

    # dynamic properties
    file_url = None

    def __init__(self, account_id=None, category=None,
                 *args, **kwargs):
        self.account_id = account_id
        self.category = category
        super(ParsingFile, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<ParsingFile %r>' % (self.filename)

    def load_urls(self, with_redirect=False, expires_in=3600,
                  thumbnail_only=False):
        """
        Populates the file_url dynamic property
        """
        s3_url = ''
        bucket_name = ''
        if not self.filename:
            return
        sub_folder = str(self.account.isin_number)
        if current_app.config['S3_UPLOAD']:
            bucket_name = current_app.config[
                'S3_SEMIDOCUMENT_BUCKET']
            s3_url = 'https://' + bucket_name + '.s3.amazonaws.com'
        else:
            signer = do_nothing
        if self.filename:
            self.file_url = os.path.join(
                s3_url, current_app.config[self.root_folder_key],
                sub_folder, self.filename)
        return
