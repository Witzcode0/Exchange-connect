"""
Models for personalised video module
"""
import os
from flask import current_app

from app import db
from app.base import constants as APP
from app.common.utils import get_s3_download_link, do_nothing
from app.base.models import BaseModel


class PersonalisedVideoMaster(BaseModel):
    __tablename__ = 'personalised_video_master'
    root_folder_key = 'PERSONALISED_VIDEO_FILE_FOLDER'
    root_video_poster_folder = 'PERSONALISED_VIDEO_POSTER_FILE_FOLDER'
    root_video_demo_folder = 'PERSONALISED_VIDEO_DEMO_FILE_FOLDER'

    created_by = db.Column(db.Integer, db.ForeignKey('user.id'),
                           nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'),
                           nullable=False)

    account_id = db.Column(db.Integer, db.ForeignKey('account.id'),
                           nullable=False)
    filename = db.Column(db.String())
    video_poster_filename = db.Column(db.String())
    video_type = db.Column(db.String(256))

    # dynamic properties
    file_url = None
    video_poster_url = None

    # relationships
    account = db.relationship('Account', backref=db.backref(
        'personalised_videos', lazy='dynamic'))

    creator = db.relationship('User', backref=db.backref(
        'videocreator', lazy='dynamic'),
                              foreign_keys='PersonalisedVideoMaster.created_by')

    profile = db.relationship('AccountProfile', backref=db.backref(
        'videoprofile', uselist=False),
        foreign_keys='PersonalisedVideoMaster.account_id',
        primaryjoin='AccountProfile.account_id == PersonalisedVideoMaster.account_id')

    def __init__(self, created_by=None, updated_by=None,
                 account_id=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        self.account_id = account_id
        super(PersonalisedVideoMaster, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<PersonalisedVideoMaster %r>' % (self.row_id)

    def load_urls(self, with_redirect=False, expires_in=3600):
        """
        Populates the file_url dynamic property
        """
        if (not self.filename and
                not self.video_poster_filename):
            return
        sub_folder = self.file_subfolder_name()
        if current_app.config['S3_UPLOAD']:
            signer = get_s3_download_link
        else:
            signer = do_nothing
        """
        if self.filename:
        self.file_url = signer(os.path.join(
        current_app.config[self.root_folder_key], sub_folder,
        self.filename), expires_in=expires_in)
        """
        if self.filename:
            if self.video_type.lower() == APP.VID_DEMO:
                self.file_url = signer(os.path.join(
                    current_app.config[self.root_video_demo_folder], sub_folder,
                    self.filename), expires_in=expires_in)
            if self.video_type.lower() == APP.VID_TEASER:
                self.file_url = signer(os.path.join(
                    current_app.config[self.root_folder_key], sub_folder,
                    self.filename), expires_in=expires_in)
        if self.video_poster_filename:
            self.video_poster_url = signer(os.path.join(
                current_app.config[self.root_video_poster_folder], sub_folder,
                self.video_poster_filename), expires_in=expires_in)
        return