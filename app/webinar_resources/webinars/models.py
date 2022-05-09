"""
Models for "webinars" package.
"""

import os

from flask import current_app
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import UniqueConstraint

from app import db
from app.common.utils import get_s3_download_link, do_nothing
from app.base.models import BaseModel
from app.base.model_fields import LCString
from app.resources.file_archives.models import ArchiveFile
# ^required for relationship


# membership table for many-to-many webinar files
webinarfile = db.Table(
    'webinarfile',
    db.Column('webinar_id', db.BigInteger, db.ForeignKey(
        'webinar.id', name='webinarfile_webinar_id_fkey', ondelete="CASCADE"),
        nullable=False),
    db.Column('file_id', db.BigInteger, db.ForeignKey(
        'archive_file.id', name='webinarfile_file_id_fkey',
        ondelete="CASCADE"), nullable=False),
    UniqueConstraint('webinar_id', 'file_id',
                     name='ac_webinar_id_file_id_key'),
)


class Webinar(BaseModel):

    __tablename__ = 'webinar'
    __global_searchable__ = ['title', 'description', 'created_by', 'is_draft',
                             'cancelled', 'open_to_account_types',
                             'open_to_public', 'started_at', 'ended_at']
    root_invite_logo_folder = 'WEBINAR_INVITE_LOGO_FILE_FOLDER'
    root_invite_banner_folder = 'WEBINAR_INVITE_BANNER_FILE_FOLDER'
    root_audio_folder = 'WEBINAR_AUDIO_FILE_FOLDER'
    root_video_folder = 'WEBINAR_VIDEO_FILE_FOLDER'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='webinar_account_id_fkey', ondelete='CASCADE'),
        nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webinar_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webinar_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)
    domain_id = db.Column(db.BigInteger, db.ForeignKey(
        'domain.id', name='webinar_domain_id_fkey', ondelete='RESTRICT'),
                          nullable=False)

    title = db.Column(db.String(256), nullable=False)
    started_at = db.Column(db.DateTime)
    ended_at = db.Column(db.DateTime)
    description = db.Column(db.String(9216))
    url = db.Column(db.String(256))
    is_draft = db.Column(db.Boolean, default=True)

    # to check if currently sending emails to invitees in background
    is_in_process = db.Column(db.Boolean, default=False)
    # to check if creator already got the mail or not , creator will not get
    #email on resend mail
    creator_mail_sent = db.Column(db.Boolean, default=False)
    # for publicly webinar
    open_to_public = db.Column(db.Boolean, default=False)
    open_to_account_types = db.Column(ARRAY(db.String(256)))
    cancelled = db.Column(db.Boolean, default=False)

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
        'webinars', lazy='dynamic'), foreign_keys='Webinar.created_by')
    account = db.relationship('Account', backref=db.backref(
        'webinars', lazy='dynamic'))
    participants = db.relationship(
        'User', secondary='webinar_participant', backref=db.backref(
            'webinar_participated', lazy='dynamic'),
        foreign_keys='[WebinarParticipant.webinar_id, '
                     'WebinarParticipant.participant_id]',
        passive_deletes=True, viewonly=True)
    hosts = db.relationship(
        'User', secondary='webinar_host', backref=db.backref(
            'webinar_hosted', lazy='dynamic'),
        foreign_keys='[WebinarHost.webinar_id, WebinarHost.host_id]',
        passive_deletes=True, viewonly=True)
    invitees = db.relationship(
        'User', secondary='webinar_invitee', backref=db.backref(
            'webinar_invited', lazy='dynamic'),
        foreign_keys='[WebinarInvitee.webinar_id, WebinarInvitee.invitee_id]',
        passive_deletes=True, viewonly=True)
    # linked files
    files = db.relationship(
        'ArchiveFile', secondary=webinarfile, backref=db.backref(
            'webinars', lazy='dynamic'), passive_deletes=True)
    # stats, as a backref (refer stats model)

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
        super(Webinar, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Webinar %r>' % (self.row_id)

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

    def sort_modified_invitees(self):
        """
        sorting participants according sequence id
        :return:
        """
        if self.webinar_invitees:
            self.webinar_invitees = sorted(
                self.webinar_invitees,
                key=lambda x: x.modified_date, reverse=True)
        return
