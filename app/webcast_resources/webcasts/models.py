"""
Models for "webcasts" package.
"""

import os

from flask import current_app
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY

from app import db
from app.common.utils import get_s3_download_link, do_nothing
from app.base.models import BaseModel
from app.base.model_fields import LCString
from app.resources.file_archives.models import ArchiveFile
# ^required for relationship


# association table for many-to-many webcast files
webcastfile = db.Table(
    'webcastfile',
    db.Column('webcast_id', db.BigInteger, db.ForeignKey(
        'webcast.id', name='webcastfile_webcast_id_fkey', ondelete="CASCADE"),
        nullable=False),
    db.Column('file_id', db.BigInteger, db.ForeignKey(
        'archive_file.id', name='webcastfile_file_id_fkey',
        ondelete="CASCADE"), nullable=False),
    UniqueConstraint('webcast_id', 'file_id',
                     name='ac_webcast_id_file_id_key'),
)


class Webcast(BaseModel):

    __tablename__ = 'webcast'

    # columns required for text searching and/or filtering in elastic search
    __global_searchable__ = ['title', 'description', 'created_by', 'is_draft',
                             'cancelled', 'started_at', 'ended_at']
    root_invite_logo_folder = 'WEBCAST_INVITE_LOGO_FILE_FOLDER'
    root_invite_banner_folder = 'WEBCAST_INVITE_BANNER_FILE_FOLDER'
    root_audio_folder = 'WEBCAST_AUDIO_FILE_FOLDER'
    root_video_folder = 'WEBCAST_VIDEO_FILE_FOLDER'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='webcast_account_id_fkey', ondelete='CASCADE'),
        nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webcast_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webcast_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)

    title = db.Column(db.String(256), nullable=False)
    started_at = db.Column(db.DateTime)
    ended_at = db.Column(db.DateTime)
    description = db.Column(db.String(9216))
    url = db.Column(db.String(256))
    is_draft = db.Column(db.Boolean, default=True)
    cancelled = db.Column(db.Boolean, default=False)

    # to check if currently sending emails to invitees in background
    is_in_process = db.Column(db.Boolean, default=False)
    # to check if creator already got the mail or not , creator will not get
    # email on resend mail
    creator_mail_sent = db.Column(db.Boolean, default=False)
    # invite section
    invite_logo_filename = db.Column(db.String(256))
    invite_banner_filename = db.Column(db.String(256))

    # saved files
    audio_filename = db.Column(db.String(256))
    video_filename = db.Column(db.String(256))

    cc_emails = db.Column(ARRAY(LCString(128)))  # for emails

    presenter_url = db.Column(db.String(256))
    conference_id = db.Column(db.String(128))
    admin_url = db.Column(db.String(256))
    recording_published = db.Column(db.Boolean, default=False, nullable=False)

    # relationships
    creator = db.relationship('User', backref=db.backref(
        'webcasts', lazy='dynamic'), foreign_keys='Webcast.created_by')
    account = db.relationship('Account', backref=db.backref(
        'webcasts', lazy='dynamic'))
    participants = db.relationship(
        'User', secondary='webcast_participant', backref=db.backref(
            'webcast_participated', lazy='dynamic'),
        foreign_keys='[WebcastParticipant.webcast_id, '
                     'WebcastParticipant.participant_id]',
        passive_deletes=True, viewonly=True)
    hosts = db.relationship(
        'User', secondary='webcast_host',
        backref=db.backref('webcast_hosted', lazy='dynamic'),
        foreign_keys='[WebcastHost.webcast_id, '
                     'WebcastHost.host_id]',
        passive_deletes=True, viewonly=True)
    invitees = db.relationship(
        'User', secondary='webcast_invitee',
        backref=db.backref(
            'webcast_invited', lazy='dynamic'),
        foreign_keys='[WebcastInvitee.webcast_id, '
                     'WebcastInvitee.invitee_id]',
        passive_deletes=True, viewonly=True)
    # linked files
    files = db.relationship(
        'ArchiveFile', secondary=webcastfile, backref=db.backref(
            'webcasts', lazy='dynamic'), passive_deletes=True)
    # stats, as a backref

    # dynamic properties
    invite_logo_url = None
    invite_banner_url = None
    audio_url = None
    video_url = None

    def __init__(self, created_by=None, updated_by=None,
                 account_id=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        self.account_id = account_id
        super(Webcast, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Webcast %r>' % (self.row_id)

    def load_urls(self, with_redirect=False, expires_in=15552000):
        """
        Populates the profile_photo_url, cover_photo_url dynamic properties
        """
        if (not self.invite_logo_filename and
                not self.invite_banner_filename and
                not self.audio_filename and not self.video_filename):
            return
        sub_folder = self.file_subfolder_name()
        if current_app.config['S3_UPLOAD']:
            signer = get_s3_download_link
        else:
            signer = do_nothing
        if self.invite_logo_filename:
            self.invite_logo_url = signer(os.path.join(
                current_app.config[self.root_invite_logo_folder], sub_folder,
                self.invite_logo_filename), expires_in=expires_in)
        if self.invite_banner_filename:
            self.invite_banner_url = signer(os.path.join(
                current_app.config[self.root_invite_banner_folder], sub_folder,
                self.invite_banner_filename), expires_in=expires_in)
        if self.audio_filename:
            self.audio_url = signer(os.path.join(
                current_app.config[self.root_audio_folder], sub_folder,
                self.audio_filename), expires_in=expires_in)
        if self.video_filename:
            self.video_url = signer(os.path.join(
                current_app.config[self.root_video_folder], sub_folder,
                self.video_filename), expires_in=expires_in)
        return
