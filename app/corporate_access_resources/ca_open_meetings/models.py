"""
Models for "corporate access open meetings" package.
"""

import os

from flask import current_app

from app import db
from app.common.utils import get_s3_download_link, do_nothing
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString
from app.resources.accounts import constants as ACCOUNT
from app.resources.cities.models import City
from app.resources.states.models import State
from app.resources.countries.models import Country
from app.resources.users.models import User
from app.resources.accounts.models import Account
from app.resources.designations import constants as DESIG
# related model imports done in corporate_access_resources/__init__


class CAOpenMeeting(BaseModel):

    __tablename__ = 'ca_open_meeting'

    root_attachment_folder = 'CA_OPEN_MEETING_ATTACHMENT_FILE_FOLDER'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='ca_open_meeting_account_id_fkey',
        ondelete='CASCADE'), nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='ca_open_meeting_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='ca_open_meeting_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)

    event_type_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_access_ref_event_type.id',
        name='ca_open_meeting_event_type_id_fkey',
        ondelete='CASCADE'), nullable=False)
    event_sub_type_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_access_ref_event_sub_type.id',
        name='ca_open_meeting_event_sub_type_id_fkey',
        ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(256), nullable=False)

    description = db.Column(db.String(9216))
    started_at = db.Column(db.DateTime)
    ended_at = db.Column(db.DateTime)
    address = db.Column(db.String(512))
    city_id = db.Column(db.BigInteger, db.ForeignKey(
        'city.id', name='ca_open_meeting_city_id_fkey'))
    state_id = db.Column(db.BigInteger, db.ForeignKey(
        'state.id', name='ca_open_meeting_state_id_fkey'))
    country_id = db.Column(db.BigInteger, db.ForeignKey(
        'country.id', name='ca_open_meeting_country_id_fkey'))

    city = db.Column(db.String(128))
    state = db.Column(db.String(128))
    country = db.Column(db.String(128))

    is_draft = db.Column(db.Boolean, default=False)

    open_to_all = db.Column(db.Boolean, default=False)
    # creator preferences for user account_types and designation
    # for open_event_meeting
    account_type_preference = db.Column(db.ARRAY(
        ChoiceString(ACCOUNT.ACCT_TYPES_CHOICES)))
    designation_preference = db.Column(db.ARRAY(
        ChoiceString(DESIG.DES_LEVEL_TYPES_CHOICES)))

    cancelled = db.Column(db.Boolean, default=False)

    attachment = db.Column(db.String(256))
    is_converted = db.Column(db.Boolean, default=False)
    dial_in_detail = db.Column(db.String(1024))
    alternative_dial_in_detail = db.Column(db.String(1024))

    # relationships
    event_type = db.relationship('CARefEventType', backref=db.backref(
        'ca_open_meetings', lazy='dynamic'),
        foreign_keys='CAOpenMeeting.event_type_id')
    event_sub_type = db.relationship('CARefEventSubType', backref=db.backref(
        'ca_open_meetings', lazy='dynamic'),
        foreign_keys='CAOpenMeeting.event_sub_type_id')
    creator = db.relationship('User', backref=db.backref(
        'ca_open_meetings', lazy='dynamic'),
        foreign_keys='CAOpenMeeting.created_by')
    account = db.relationship('Account', backref=db.backref(
        'ca_open_meetings', lazy='dynamic'))
    # linked files
    participants = db.relationship(
        'User', secondary='ca_open_meeting_participant',
        backref=db.backref(
            'ca_open_meeting_participated_j', lazy='dynamic'),
        foreign_keys='[CAOpenMeetingParticipant.'
                     'ca_open_meeting_id, '
                     'CAOpenMeetingParticipant.participant_id]',
        passive_deletes=True, viewonly=True)
    invitees = db.relationship(
        'User', secondary='ca_open_meeting_invitee',
        backref=db.backref(
            'ca_open_meeting_invited', lazy='dynamic'),
        foreign_keys='[CAOpenMeetingInvitee.ca_open_meeting_id, '
                     'CAOpenMeetingInvitee.invitee_id]',
        passive_deletes=True, viewonly=True)
    # joined_invitees = db.relationship(
    #     'User', secondary='corporate_access_event_invitee',
    #     backref=db.backref('events_joined_invitees', lazy='dynamic'),
    #     foreign_keys='[CorporateAccessEventInvitee.corporate_access_event_id, '
    #                  'CorporateAccessEventInvitee.invitee_id]',
    #     primaryjoin="and_(CorporateAccessEventInvitee.status == '"
    #                 "" + CORPORATEACCESSEVENTINVITEE.JOINED +
    #                 "', CorporateAccessEventInvitee.corporate_access_event_id "
    #                 "== CorporateAccessEvent.row_id)",
    #     secondaryjoin="CorporateAccessEventInvitee.invitee_id == User.row_id",
    #     viewonly=True)

    def __init__(self, created_by=None, updated_by=None,
                 account_id=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        self.account_id = account_id
        super(CAOpenMeeting, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CAOpenMeeting %r>' % (self.row_id)

    def load_urls(self, with_redirect=False, expires_in=15552000):
        """
        Populates the profile_photo_url, cover_photo_url dynamic properties
        """
        if not self.attachment:
            return
        sub_folder = self.file_subfolder_name()
        if current_app.config['S3_UPLOAD']:
            signer = get_s3_download_link
        else:
            signer = do_nothing
        if self.attachment:
            self.attachment_url = signer(os.path.join(
                current_app.config[self.root_attachment_folder], sub_folder,
                self.attachment), expires_in=expires_in)
        return

    def sort_participants_and_slots(self):
        """
        sorting participants according sequence id
        sorting slots according started datetime
        :return:
        """
        if self.ca_open_meeting_participants:
            self.ca_open_meeting_participants = sorted(
                self.ca_open_meeting_participants,
                key=lambda x: x.sequence_id)

        if self.slots:
            self.slots = sorted(self.slots, key=lambda x: x.started_at)
        return
