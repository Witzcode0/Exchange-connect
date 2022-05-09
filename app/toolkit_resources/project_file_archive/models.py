"""
Models for "project file archives" package.
"""

import os

from flask import current_app

from app import db
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString
from app.common.utils import get_s3_download_link, do_nothing
from app.toolkit_resources.projects import constants as PROJECT
# related model imports done in toolkit/__init__


class ProjectArchiveFile(BaseModel):

    __tablename__ = 'project_archive_file'
    # config key for root folder of files
    root_folder_key = 'PROJECT_ARCHIVE_FILE_FOLDER'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='project_archive_file_created_by_fkey'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='project_archive_file_updated_by_fkey'),
        nullable=False)

    file_type = db.Column(db.String(256))
    filename = db.Column(db.String())
    file_major_type = db.Column(db.String(128))
    category = db.Column(ChoiceString(PROJECT.PROJECT_FILE_CATEGORY_CHOICES))

    # account id of the project
    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='project_archive_file_account_id_fkey'),
        nullable=False)
    project_id = db.Column(db.BigInteger, db.ForeignKey(
        'project.id', name='project_archive_file_project_id_fkey',
        ondelete='CASCADE'), nullable=False)
    project_parameter_id = db.Column(db.BigInteger, db.ForeignKey(
        'project_parameter.id',
        name='project_archive_file_project_parameter_id_fkey',
        ondelete='SET NULL'))
    remarks = db.Column(db.String(1024))
    version = db.Column(db.String(32))

    # deleted bit
    deleted = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)
    # only to control file visibility by prime communicator
    visible_to_client = db.Column(db.Boolean, default=True, nullable=False)

    # relationships
    account = db.relationship('Account', backref=db.backref(
        'project_files', lazy='dynamic'))
    creator = db.relationship('User', backref=db.backref(
        'project_files', lazy='dynamic'),
        foreign_keys='ProjectArchiveFile.created_by')
    project = db.relationship('Project', backref=db.backref(
        'project_files', lazy='dynamic', passive_deletes=True),
        foreign_keys='ProjectArchiveFile.project_id')
    project_parameter = db.relationship('ProjectParameter', backref=db.backref(
        'project_files', lazy='dynamic'),
        foreign_keys='ProjectArchiveFile.project_parameter_id')

    # dynamic properties
    file_url = None
    # number of unread comments for the current user
    unread_comments = None

    def __init__(self, created_by=None, updated_by=None, account_id=None,
                 category=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        self.account_id = account_id
        self.category = category
        super(ProjectArchiveFile, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<ProjectArchiveFile %r>' % (self.row_id)

    def load_urls(self, with_redirect=False, expires_in=3600):
        """
        Populates the file_url dynamic property
        """
        if not self.filename:
            return
        sub_folder = self.file_subfolder_name()
        if current_app.config['S3_UPLOAD']:
            signer = get_s3_download_link
        else:
            signer = do_nothing
        if self.filename:
            self.file_url = signer(os.path.join(
                current_app.config[self.root_folder_key], sub_folder,
                self.filename), expires_in=expires_in)
        return
