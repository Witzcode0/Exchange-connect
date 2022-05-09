"""
Models for "activities" package.
"""

import os

from flask import current_app
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app import db
from app.common.utils import get_s3_download_link, do_nothing
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString, LCString,CastingArray
# from app.resources.contacts import constants as CONTACT
from app.resources.accounts import constants as ACCOUNT
from app.activity.activities import constants as ACTIVITY
from app.resources.activity_type.models import ActivityType
from app.activity.activities_institution.models import ActivityInstitution, ActivityInstitutionParticipant
from app.activity.activities_organiser.models import ActivityOrganiser, ActivityOrganiserParticipant
from app.activity.activities_representative.models import ActivityRepresentative
from app.resources.reminders.models import Reminder
# ^ import is needed for relationship


# membership table for many-to-many webinar files
activityfile = db.Table(
    'activityfile',
    db.Column('activity_id', db.BigInteger, db.ForeignKey(
        'activity.id', name='activityfile_activity_id_fkey', ondelete="CASCADE"),
        nullable=False),
    db.Column('file_id', db.BigInteger, db.ForeignKey(
        'archive_file.id', name='activityfile_file_id_fkey',
        ondelete="CASCADE"), nullable=False),
    UniqueConstraint('activity_id', 'file_id',
                     name='ac_activity_id_file_id_key'),
)

# association table for many-to-many activity participants
activityuser = db.Table(
    'activityuser',
    db.Column('activity_id', db.Integer, db.ForeignKey(
        'activity.id', ondelete="CASCADE"), nullable=False),
    db.Column('user_id', db.Integer, db.ForeignKey(
        'user.id', ondelete="CASCADE"), nullable=False),
    UniqueConstraint('activity_id', 'user_id',
                     name='ac_activity_id_user_id_key'),
)


class Activity(BaseModel):

    __tablename__ = 'activity'
    __global_searchable__ = ['subject', 'description', 'highlights', 'notes',
                            'purpose', 'name', 'created_by']
    # config key for root folder of documents
    # root_folder_key = 'ACTIVITY_DOCS_FOLDER'

    created_by = db.Column(db.Integer, db.ForeignKey(
        'user.id', name='activity_created_by_fkey'), nullable=False)
    # activity details
    # common details for all types of activities, these will be always present
    # i.e required
    activity_type = db.Column(db.Integer, db.ForeignKey(
        'activity_type.id', name='activity_type_created_by_fkey'), nullable=False)
    agenda = db.Column(db.String(256), nullable=False)

    documents = db.Column(db.ARRAY(db.String))
    highlights = db.Column(db.String(1024))
    notes = db.Column(db.String(1024))
    meeting_url = db.Column(db.String(256))
    started_at = db.Column(db.DateTime)
    ended_at = db.Column(db.DateTime)
    priority = db.Column(db.Enum(
        *ACTIVITY.PRIORITY_TYPES, name="priority_types"))
    repeat_type = db.Column(db.Enum(
        *ACTIVITY.REPEAT_TYPES, name="repeat_types"))
    repeat_start = db.Column(db.DateTime)
    repeat_end = db.Column(db.DateTime)
    venue = db.Column(db.String(256))
    deleted_participants = db.Column(db.ARRAY(db.String()))

    # reminders
    reminder_set = db.Column(db.Boolean)
    # reminder_start = db.Column(db.DateTime)
    # reminder_frequency = db.Column(ChoiceString(
    #     ACTIVITY.REMINDER_FREQUENCY_TYPES_CHOICES), default=None)
    reminder_type = db.Column(db.Enum(
        *ACTIVITY.REMINDER_TYPES, name="reminder_types"))
    account_type = db.Column(ChoiceString(ACTIVITY.AC_TYPES_CHOICE))

    reminder_time = db.Column(db.Integer)
    reminder_unit = db.Column(ChoiceString(ACTIVITY.RM_UNITS_CHOICES))
    # deleted bit
    deleted = db.Column(db.Boolean, default=False)

    # relationships
    activity_types = db.relationship('ActivityType', backref=db.backref(
        'activity_type_user_activity', uselist=True),
        primaryjoin='Activity.activity_type == ActivityType.row_id')
    participants = db.relationship(
        'User', secondary=activityuser, backref=db.backref(
            'activities', lazy='dynamic'), passive_deletes=True)
    creator = db.relationship('User', backref=db.backref(
        'activity_list_creator', lazy='dynamic'),
    foreign_keys='Activity.created_by')
    organiser_participants = db.relationship(
        'ActivityOrganiserParticipant', backref=db.backref(
            'activities_orgaiser_participants'))
    organiser = db.relationship(
        'ActivityOrganiser', backref=db.backref(
            'activities_orgaiser'))
    institution_participants = db.relationship( 
        'ActivityInstitutionParticipant', backref=db.backref(
            'activities_institution_participants'))
    institution = db.relationship( 
        'ActivityInstitution', backref=db.backref(
            'activities_institution'))
    representatives = db.relationship(
        'ActivityRepresentative', backref=db.backref(
            'activity_representative'))
    reminders = db.relationship(
        'Reminder', backref=db.backref(
            'actyivity_reminder'), passive_deletes=True)
    # crm_participants = db.relationship(
    #     'CRMContact', secondary=taskassigned, backref=db.backref(
    #         'tasks', lazy='dynamic'), passive_deletes=True)
    user = db.relationship('User')
    # linked files
    files = db.relationship(
        'ArchiveFile', secondary=activityfile, backref=db.backref(
            'activity', lazy='dynamic'), passive_deletes=True)

    # dynamic properties
    # document_urls = None
    _all_participants_dict = None

    # New instance instantiation procedure
    def __init__(self, activity_type=None, created_by=None, assigned_to=None,
                 subject=None, *args, **kwargs):
        self.activity_type = activity_type
        self.created_by = created_by
        self.assigned_to = assigned_to
        self.subject = subject
        super(Activity, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Activity %r>' % (self.row_id)

    def _make_all_participants_dict(self):
        """
        Makes a dictionary of all participants in the activity, useful for
        loading meeting participants.
        """
        if self._all_participants_dict:
            return
        # default
        self._all_participants_dict = {}
        if not self.participants:
            return
        # build list
        self._all_participants_dict = {p.row_id: p for p in self.participants}

    def load_meeting_participants(self):
        """
        Populates the participants dynamic property of "meetings"
        """
        if not self.meetings:
            return
        self._make_all_participants_dict()

        if self.meetings:
            for meet in self.meetings:
                if 'participant_ids' not in meet:
                    continue
                meet['participants'] = [self._all_participants_dict[pid]
                                        for pid in meet['participant_ids']]
        return
