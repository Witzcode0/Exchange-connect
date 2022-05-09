"""
Models for "corporate announcements" package.
"""
import os

from flask import current_app

from app import db
from app.common.utils import get_s3_download_link, do_nothing
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString
from app.resources.corporate_announcements import constants as \
    CORP_ANNOUNCEMENT
from app.corporate_access_resources.corporate_access_events.models import (
    CorporateAccessEvent)
from app.resources.descriptor.models import BSE_Descriptor
from app.resources.corporate_announcements_category.models import CorporateAnnouncementCategory
# from app.resources.bse.models import BSE_Descriptor

class CorporateAnnouncement(BaseModel):

    __tablename__ = 'corporate_announcement'
    __global_searchable__ = ['subject', 'description', 'category',
                             'announcement_date']
    # config key for root folder of files
    root_file_folder_key = 'CORPORATE_ANNOUNCEMENT_FILE_FOLDER'

    account_id = db.Column(db.Integer, db.ForeignKey('account.id'),
                           nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'),
                           nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'),
                           nullable=False)

    announcement_date = db.Column(db.DateTime, nullable=False)
    category = db.Column(ChoiceString(
        CORP_ANNOUNCEMENT.CANNC_CATEGORY_TYPES_CHOICES))

    subject = db.Column(db.String(512))
    description = db.Column(db.String(2048))

    # check if both of these are present
    file = db.Column(db.String())
    url = db.Column(db.String(256))

    # announcement as a CAEvent
    ca_event_audio_file_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_access_event.id',
        name='announcement_ca_event_audio_file_id_fkey',
        ondelete='CASCADE'))
    ca_event_transcript_file_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_access_event.id',
        name='announcement_ca_event_transcript_file_id_fkey',
        ondelete='CASCADE'))

    bse_type_of_announce = db.Column(db.String())

    bse_descriptor = db.Column(db.BigInteger, db.ForeignKey(
        'descriptor_master.id',
        name='fk_bse_descriptor_id'))

    source = db.Column(db.String())
    category_id = db.Column(db.Integer, db.ForeignKey('corporate_announcement_category.id'))

    # deleted bit
    deleted = db.Column(db.Boolean, default=False)

    # relationships
    account = db.relationship('Account', backref=db.backref(
        'announcements', lazy='dynamic'))
    creator = db.relationship('User', backref=db.backref(
        'announcements', lazy='dynamic'),
        foreign_keys='CorporateAnnouncement.created_by')
    editor = db.relationship('User', backref=db.backref(
        'updated_announcements', lazy='dynamic'),
        foreign_keys='CorporateAnnouncement.updated_by')

    ca_event_audio_file = db.relationship(
        'CorporateAccessEvent', backref=db.backref(
            'ca_audio_announcements', uselist=False, passive_deletes=True),
        primaryjoin='CorporateAnnouncement.ca_event_audio_file_id '
        '== CorporateAccessEvent.row_id')

    ca_event_transcript_file = db.relationship(
        'CorporateAccessEvent', backref=db.backref(
            'ca_transcript_announcements', uselist=False, passive_deletes=True),
        primaryjoin='CorporateAnnouncement.ca_event_transcript_file_id '
                    '== CorporateAccessEvent.row_id')

    bse_descriptors = db.relationship('BSE_Descriptor', backref=db.backref(
        'bse_descriptor', uselist=False, passive_deletes=True),
                             primaryjoin='CorporateAnnouncement.bse_descriptor == BSE_Descriptor.row_id')
    ec_category = db.relationship('CorporateAnnouncementCategory',
                            backref=db.backref('category_id', uselist=False),
                            primaryjoin='CorporateAnnouncement.category_id == CorporateAnnouncementCategory.row_id')


    # dynamic properties
    file_url = None

    def __init__(self, row_id=None, *args, **kwargs):
        self.row_id = row_id
        super(CorporateAnnouncement, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CorporateAnnouncement %r>' % (self.subject)

    def load_urls(self, with_redirect=False, expires_in=3600):
        """
        Populates the file_url dynamic properties
        """
        if not self.file:
            return
        sub_folder = self.file_subfolder_name()
        if current_app.config['S3_UPLOAD']:
            signer = get_s3_download_link
        else:
            signer = do_nothing
        if self.file:
            self.file_url = signer(os.path.join(
                current_app.config[self.root_file_folder_key],
                sub_folder, self.file), expires_in=expires_in)
        return
