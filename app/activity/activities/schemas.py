"""
Schemas for "activities" related models
"""

from flask import g
from marshmallow import (
    fields, validate, pre_dump, validates_schema, ValidationError)
from marshmallow_sqlalchemy import field_for
from sqlalchemy.orm import load_only
from sqlalchemy import and_, any_, func, or_
from sqlalchemy.orm import load_only, joinedload

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.resources.users.models import User
from app.crm_resources.crm_contacts.models import CRMContact
from app.resources.contacts.models import Contact
from app.activity.activities import constants as ACTIVITY
from app.activity.activities.models import Activity
# from app.activities_institution.models import ActivityInstitution
from app.activity.activities_institution.schemas import ActivityInstitutionSchema, ActivityInstitutionParticipantSchema
from app.activity.activities_organiser.schemas import ActivityOrganiserSchema, ActivityOrganiserParticipantSchema
from app.activity.activities_representative.schemas import ActivityRepresentativeSchema
from app.resources.accounts.models import Account
from app.resources.reminders.schemas import ReminderSchema
from app.resources.file_archives.models import ArchiveFile


# contact details that will be passed while populating participants
participants_fields = [
    'row_id']
# user details that will be passed while populating assignees
assignee_fields = ['row_id', 'first_name', 'last_name', 'links']

class ActivitySchema(ma.ModelSchema):
    """
    Schema for loading "activity" from request, and also formatting output.
    *** Don't use this as a global, as it stores _cached_contacts, which would
    change from request to request.
    """
    _cached_contacts = None  # while validating existance of contacts,
    _cached_users = None  # while validating existance of users
    _cached_participant = None
    # we populate this for avoiding repeat query
    _default_exclude_fields = [
        "description","contact_type","email_notification","sub_type","name","status",
        "repeat_type","repeat_start","repeat_end","purpose","call_result","venue_street","venue_street2",
        "venue_city","venue_state","venue_zip","venue_country","sector","all_day","host","company",
        "company_id","meetings","deleted_participants","reminder_start","reminder_frequency",
        "crm_participants","location"]

    class Meta:
        model = Activity
        include_fk = True
        load_only = ('deleted', 'created_by', 'account_id', )
        dump_only = default_exclude + ('deleted', 'created_by', 'account_id',
                                       'status')

    participants = ma.List(ma.Nested(
        'app.resources.users.schemas.UserSchema',
        only=user_fields))
    representatives = ma.List(ma.Nested(ActivityRepresentativeSchema,
        dump_only=True))
    organiser_participants = ma.List(ma.Nested(ActivityOrganiserParticipantSchema,
        dump_only=True))
    organiser = ma.List(ma.Nested(ActivityOrganiserSchema,
        dump_only=True))
    institution_participants = ma.List(ma.Nested(ActivityInstitutionParticipantSchema, 
        dump_only=True))
    institution =ma.List(ma.Nested(ActivityInstitutionSchema, 
        dump_only=True))
    reminders =ma.List(ma.Nested(ReminderSchema,
        dump_only=True))
    activity_types = ma.Nested(
        'app.resources.activity_type.schemas.ActivityTypeSchema',
        only=('row_id','activity_name'))
    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    files = ma.List(ma.Nested(
        'app.resources.file_archives.schemas.ArchiveFileSchema',
        only=['row_id', 'filename', 'file_type', 'file_major_type',
              'file_url', 'thumbnail_url']), dump_only=True)

    @validates_schema(pass_original=True)
    def validate_participant_ids(self, data, original_data):
        """
        Validate that the participant_ids contacts exist, these can be passed
        as part of main activity, or part of sub activity, i.e "roadshow"
        meetings
        """
        error = False
        missing = []
        self._cached_contacts = []
        # load all the participant ids
        pids = []
        if ('invitee_ids' in original_data and
                original_data['invitee_ids']):
            pids = original_data['invitee_ids'][:]
        # if 'meetings' in data and data['meetings']:
        #     for meet in data['meetings']:
        #         if 'invitee_ids' in meet and meet['invitee_ids']:
        #             pids.extend(meet['invitee_ids'])
        # validate contact_ids, and load all the _cached_contacts
        if pids:
            # make query
            cids = []
            invitee_ids = []
            for cid in pids:
                try:
                    cids.append(int(cid))
                except Exception as e:
                    continue
            for pid in cids:
                contacts = Contact.query.filter(or_(
                    and_(Contact.sent_by.in_([pid]), Contact.sent_to ==
                         g.current_user['row_id']),
                    and_(Contact.sent_to.in_([pid]), Contact.sent_by ==
                         g.current_user['row_id']))).all()
                if contacts:
                    invitee_ids.append(pid)
                    user_pid = User.query.get(pid)
                    self._cached_contacts.append(user_pid)

            missing = set(cids) - set(invitee_ids)
            if missing:
                error = True

        if error:
            raise ValidationError(
                'Contacts: %s do not exist' % missing,
                'invitee_ids'
            )


    @validates_schema(pass_original=True)
    def validate_file_ids(self, data, original_data):

        # file exists or not
        self._cached_files = []
        missing_files = []
        error_files = False
        # load all the file ids
        f_ids = []
        if 'file_ids' in original_data and original_data['file_ids']:
            f_ids = original_data['file_ids'][:]
        # validate file_ids, and load all the _cached_files
        if f_ids:
            # make query
            fids = []
            for f in f_ids:
                try:
                    fids.append(int(f))
                except Exception as e:
                    continue
            self._cached_files = [f for f in ArchiveFile.query.filter(
                ArchiveFile.row_id.in_(fids)).options(load_only(
                    'row_id', 'deleted')).all() if not f.deleted]
            file_ids = [f.row_id for f in self._cached_files]
            missing_files = set(fids) - set(file_ids)
            if missing_files:
                error_files = True

        if error_files:
            raise ValidationError(
                'Files: %s do not exist' % missing_files,
                'file_ids'
            )

class ActivityReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "activity" filters from request args
    """
    # standard db fields
    activity_name = fields.String(load_only=True)
    agenda = fields.String(load_only=True)
    activity_type = fields.Integer(load_only=True)
    account_name = fields.String(load_only=True)
    from_date = fields.DateTime(load_only=True)
    to_date = fields.DateTime(load_only=True)
