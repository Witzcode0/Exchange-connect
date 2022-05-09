"""
Models for "crm distribution list" package.
"""

import os

from flask import current_app
from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.common.utils import get_s3_download_link, do_nothing, get_s3_file_size
from app.crm_resources.crm_distribution_file_library.models import (
    CRMDistributionLibraryFile)

# association table for many-to-many event files
distributionfiles = db.Table(
    'distributionfiles',
    db.Column('distribution_id', db.BigInteger, db.ForeignKey(
        'crm_distribution_list.id',
        name='distributionfiles_distribution_id_fkey',
        ondelete="CASCADE"), nullable=False),
    db.Column('file_id', db.Integer, db.ForeignKey(
        'crm_distribution_library_file.id',
        name='distributionfiles_file_id_fkey', ondelete="CASCADE"),
              nullable=False),
    UniqueConstraint('distribution_id', 'file_id',
                     name='ac_distribution_id_file_id_key'),
)


class CRMDistributionList(BaseModel):

    __tablename__ = 'crm_distribution_list'
    __global_searchable__ = ['campaign_name', 'is_draft', 'created_by',
                             'created_date']
    root_attachment_folder_key = 'CRM_DISTLIST_ATTACH_FOLDER'

    account_id = db.Column(db.Integer, db.ForeignKey('account.id'),
                           nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'),
                           nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'),
                           nullable=False)

    campaign_name = db.Column(db.String(256), nullable=False)
    html_template = db.Column(db.String, nullable=False)
    attachments = db.Column(db.ARRAY(db.String))

    is_draft = db.Column(db.Boolean, default=True)
    # relationship
    html_files = db.relationship(
        'CRMDistributionLibraryFile', secondary=distributionfiles,
        backref=db.backref('crm_distribution_lists', lazy='dynamic'),
        passive_deletes=True)

    account = db.relationship('Account', backref=db.backref(
        'crm_distribution_list', lazy='dynamic'))

    # dynamic properties
    attachment_urls = []
    file_attachment_size = []

    def __init__(self, campaign_name=None, created_by=None, *args, **kwargs):
        self.campaign_name = campaign_name
        self.created_by = created_by
        super(CRMDistributionList, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CRMDistributionList %r>' % (self.campaign_name)

    def load_urls(self, with_redirect=False, expires_in=3600):
        """
        Populates the attachment file urls dynamic properties
        """
        s3_url = ''
        if not self.attachments:
            return
        sub_folder = self.file_subfolder_name()
        if current_app.config['S3_UPLOAD']:
            signer = get_s3_download_link
        else:
            signer = do_nothing

        if self.attachments:
            self.attachment_urls = []
            self.file_attachment_size = []
            for attch in self.attachments:
                file_with_size = {}
                self.attachment_urls.append(signer(os.path.join(
                    current_app.config[self.root_attachment_folder_key],
                    sub_folder, attch), expires_in=expires_in))
                # get file size from s3
                file_with_size['attachment_name'] = attch
                file_with_size['size'] = get_s3_file_size(os.path.join(
                    current_app.config[self.root_attachment_folder_key],
                    sub_folder, attch))
                self.file_attachment_size.append(file_with_size)
        return
