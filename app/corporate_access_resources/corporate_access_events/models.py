"""
Models for "corporate access events" package.
"""

import os

from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import UniqueConstraint
from flask import current_app

from app import db
from app.common.utils import get_s3_download_link, do_nothing, custom_sorted
from app.base.models import BaseModel
from app.base.model_fields import LCString, ChoiceString
from app.resources.accounts import constants as ACCOUNT
from app.corporate_access_resources.corporate_access_event_invitees import (
    constants as CORPORATEACCESSEVENTINVITEE)
from app.resources.cities.models import City
from app.resources.states.models import State
from app.resources.countries.models import Country
from app.resources.file_archives.models import ArchiveFile
# related model imports done in corporate_access_resources/__init__


# association table for many-to-many CorporateAccessEvent files
corporateaccesseventfiles = db.Table(
    'corporateaccesseventfiles',
    db.Column('corporate_access_event_id', db.BigInteger, db.ForeignKey(
        'corporate_access_event.id',
        name='corporateaccesseventfiles_event_id_fkey', ondelete="CASCADE"),
        nullable=False),
    db.Column('file_id', db.BigInteger, db.ForeignKey(
        'archive_file.id', name='corporateaccesseventfiles_file_id_fkey',
        ondelete="CASCADE"), nullable=False),
    UniqueConstraint('corporate_access_event_id', 'file_id',
                     name='ac_corporate_access_event_id_file_id_key'),
)

caeventparticipantcompanies = db.Table(
    'caeventparticipantcompanies',
    db.Column('corporate_access_event_id', db.BigInteger, db.ForeignKey(
        'corporate_access_event.id',
        name='caeventparticipantscompanies_event_id_fkey', ondelete="CASCADE"),
        nullable=False),
    db.Column('company_id', db.BigInteger, db.ForeignKey(
            'account.id', name='caeventparticipantscompanies_company_id_fkey',
            ondelete="CASCADE"), nullable=False),
    UniqueConstraint('corporate_access_event_id', 'company_id',
                     name='ac_corporate_access_event_id_company_id_key'),
)


class CorporateAccessEvent(BaseModel):

    __tablename__ = 'corporate_access_event'
    __global_searchable__ = ['title', 'description', 'open_to_all',
                             'created_by', 'is_draft', 'cancelled',
                             'started_at', 'ended_at',
                             'account_type_preference']
    root_invite_logo_folder = 'CA_EVENT_INVITE_LOGO_FILE_FOLDER'
    root_invite_banner_folder = 'CA_EVENT_INVITE_BANNER_FILE_FOLDER'
    root_audio_folder = 'CA_EVENT_AUDIO_FILE_FOLDER'
    root_video_folder = 'CA_EVENT_VIDEO_FILE_FOLDER'
    root_attachment_folder = 'CA_EVENT_ATTACHMENT_FILE_FOLDER'
    root_transcript_folder = 'CA_EVENT_TRANSCRIPT_FILE_FOLDER'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='corporate_access_event_account_id_fkey',
        ondelete='CASCADE'), nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='corporate_access_event_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)

    event_type_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_access_ref_event_type.id',
        name='corporate_access_event_event_type_id_fkey',
        ondelete='CASCADE'), nullable=False)
    event_sub_type_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_access_ref_event_sub_type.id',
        name='corporate_access_event_event_sub_type_id_fkey',
        ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(256), nullable=False)

    description = db.Column(db.String(9216))
    started_at = db.Column(db.DateTime)
    ended_at = db.Column(db.DateTime)

    dial_in_detail = db.Column(db.String(1024))
    alternative_dial_in_detail = db.Column(db.String(1024))

    city_id = db.Column(db.BigInteger, db.ForeignKey(
        'city.id', name='corporate_access_event_city_id_fkey'))
    state_id = db.Column(db.BigInteger, db.ForeignKey(
        'state.id', name='corporate_access_event_state_id_fkey'))
    country_id = db.Column(db.BigInteger, db.ForeignKey(
        'country.id', name='corporate_access_event_country_id_fkey'))

    city = db.Column(db.String(128))
    state = db.Column(db.String(128))
    country = db.Column(db.String(128))

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
    attachment = db.Column(db.String(256))

    # saved files
    audio_filename = db.Column(db.String(256))
    video_filename = db.Column(db.String(256))
    transcript_filename = db.Column(db.String(256))

    cc_emails = db.Column(ARRAY(LCString(128)))  # for emails

    is_open_meeting = db.Column(db.Boolean, default=False)
    # for system user only
    open_to_all = db.Column(db.Boolean, default=False)
    # creator preferences for user account_types and designation
    # for open_event_meeting
    account_type_preference = db.Column(db.ARRAY(
        ChoiceString(ACCOUNT.ACCT_TYPES_CHOICES)))
    # for one-to-one meeting
    caevent_support = db.Column(db.Boolean, default=False)
    flexibility = db.Column(db.Boolean, default=False)
    remark = db.Column(db.String(2048))
    other_invitees = db.Column(db.String(1024))

    # relationships
    event_type = db.relationship('CARefEventType', backref=db.backref(
        'corporate_access_events', lazy='dynamic'),
        foreign_keys='CorporateAccessEvent.event_type_id')
    event_sub_type = db.relationship('CARefEventSubType', backref=db.backref(
        'corporate_access_events', lazy='dynamic'),
        foreign_keys='CorporateAccessEvent.event_sub_type_id')
    creator = db.relationship('User', backref=db.backref(
        'corporate_access_events', lazy='dynamic'),
        foreign_keys='CorporateAccessEvent.created_by')
    account = db.relationship('Account', backref=db.backref(
        'corporate_access_events', lazy='dynamic'))
    # linked files
    files = db.relationship(
        'ArchiveFile', secondary=corporateaccesseventfiles,
        backref=db.backref('corporateaccessevents', lazy='dynamic'),
        passive_deletes=True)
    caevent_participant_companies = db.relationship(
        'Account', secondary=caeventparticipantcompanies,
        backref=db.backref('corporateaccessevents', lazy='dynamic'),
        passive_deletes=True)
    participants = db.relationship(
        'User', secondary='corporate_access_event_participant',
        backref=db.backref(
            'corporate_access_event_participated', lazy='dynamic'),
        foreign_keys='[CorporateAccessEventParticipant.'
                     'corporate_access_event_id, '
                     'CorporateAccessEventParticipant.participant_id]',
        passive_deletes=True, viewonly=True)
    hosts = db.relationship(
        'User', secondary='corporate_access_event_host',
        backref=db.backref(
            'corporate_access_event_hosted', lazy='dynamic'),
        foreign_keys='[CorporateAccessEventHost.corporate_access_event_id, '
                     'CorporateAccessEventHost.host_id]',
        passive_deletes=True, viewonly=True)
    invitees = db.relationship(
        'User', secondary='corporate_access_event_invitee',
        backref=db.backref(
            'corporate_access_event_invited', lazy='dynamic'),
        foreign_keys='[CorporateAccessEventInvitee.corporate_access_event_id, '
                     'CorporateAccessEventInvitee.invitee_id]',
        passive_deletes=True, viewonly=True)
    joined_invitees = db.relationship(
        'User', secondary='corporate_access_event_invitee',
        backref=db.backref('events_joined_invitees', lazy='dynamic'),
        foreign_keys='[CorporateAccessEventInvitee.corporate_access_event_id, '
                     'CorporateAccessEventInvitee.user_id]',
        primaryjoin="and_(CorporateAccessEventInvitee.status == '"
                    "" + CORPORATEACCESSEVENTINVITEE.JOINED +
                    "', CorporateAccessEventInvitee.corporate_access_event_id "
                    "== CorporateAccessEvent.row_id)",
        secondaryjoin="CorporateAccessEventInvitee.user_id == User.row_id",
        viewonly=True)
    # stats, as a backref (refer stats model)

    # dynamic properties
    invite_logo_url = None
    invite_banner_url = None
    audio_url = None
    video_url = None
    transcript_url = None
    attachment_url = None

    def __init__(self, created_by=None, updated_by=None,
                 account_id=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        self.account_id = account_id
        super(CorporateAccessEvent, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CorporateAccessEvent %r>' % (self.row_id)

    def load_urls(self, with_redirect=False, expires_in=15552000):
        """
        Populates the profile_photo_url, cover_photo_url dynamic properties
        """
        if (not self.invite_logo_filename and
                not self.invite_banner_filename and
                not self.audio_filename and not self.video_filename and
                not self.attachment and not self.transcript_filename):
            return
        sub_folder = self.file_subfolder_name()
        if current_app.config['S3_UPLOAD']:
            signer = get_s3_download_link
        else:
            signer = do_nothing
        if self.invite_logo_filename:
            self.invite_logo_url = signer(os.path.join(
                current_app.config[self.root_invite_logo_folder],
                sub_folder, self.invite_logo_filename), expires_in=expires_in)
        if self.invite_banner_filename:
            self.invite_banner_url = signer(os.path.join(
                current_app.config[self.root_invite_banner_folder], sub_folder,
                self.invite_banner_filename), expires_in=expires_in)
        if self.audio_filename:
            self.audio_url = signer(os.path.join(
                current_app.config[self.root_audio_folder], sub_folder,
                self.audio_filename), expires_in=expires_in)
        if self.transcript_filename:
            self.transcript_url = signer(os.path.join(
                current_app.config[self.root_transcript_folder], sub_folder,
                self.transcript_filename), expires_in=expires_in)
        if self.video_filename:
            self.video_url = signer(os.path.join(
                current_app.config[self.root_video_folder], sub_folder,
                self.video_filename), expires_in=expires_in)
        if self.attachment:
            self.attachment_url = signer(os.path.join(
                current_app.config[self.root_attachment_folder], sub_folder,
                self.attachment), expires_in=expires_in)
        return

    def sort_rsvps_and_participants(self):
        """
        sorting participants according sequence id
        :return:
        """
        if self.corporate_access_event_participants:
            self.corporate_access_event_participants = custom_sorted(
                self.corporate_access_event_participants,
                key=lambda x: x.sequence_id)

        if self.rsvps:
            self.rsvps = custom_sorted(self.rsvps,
                key=lambda x: x.sequence_id)
        return
