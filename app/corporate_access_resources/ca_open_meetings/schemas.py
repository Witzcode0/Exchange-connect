"""
Schemas for "ca open meeting" related models
"""

from marshmallow import (
    fields, validate, pre_dump, validates_schema, ValidationError)
from marshmallow_sqlalchemy import field_for
from sqlalchemy.orm import load_only
from flask import g
from sqlalchemy import and_, or_

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.base import constants as APP
from app.resources.accounts import constants as ACCOUNT
from app.resources.designations import constants as DESIG
from app.resources.users.models import User
from app.corporate_access_resources.ca_open_meetings.models import \
    CAOpenMeeting
from app.corporate_access_resources.corporate_access_events import \
    constants as CAEVENT
from app.corporate_access_resources.ref_event_sub_types.models import \
    CARefEventSubType
from app.corporate_access_resources.ca_open_meeting_invitees.schemas import \
    CAOpenMeetingInviteeSchema
from app.corporate_access_resources.ca_open_meeting_participants.schemas \
    import CAOpenMeetingParticipantSchema
from app.corporate_access_resources.ca_open_meeting_slots.schemas import \
    CAOpenMeetingSlotSchema


# account details that will be passed while populating account relation
account_fields = ['row_id', 'links', 'account_name', 'account_type']
# slot fields that will be passed while populating slot relation
slot_fields = ['row_id', 'started_at', 'ended_at', 'slot_type', 'description',
               'bookable_seats', 'booked_seats', 'address', 'event_id',
               'slot_name', 'text_1', 'text_2', 'available_seats', 'rejected',
               'ca_open_meeting_inquiries', 'disallowed', 'rejected_inquiries']

# user details that will be passed while populating user relation
creator_user_fields = user_fields + ['account.profile.profile_thumbnail_url']


class CAOpenMeetingSchema(ma.ModelSchema):
    """
    Schema for loading "Corporate Access Event" from request,
    and also formatting output
    """

    title = field_for(CAOpenMeeting, 'title', validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=CAEVENT.COMMON_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    description = field_for(CAOpenMeeting, 'description', validate=[
        validate.Length(max=CAEVENT.DESCRIPTION_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    account_type_preference = fields.List(field_for(
        CAOpenMeeting, 'account_type_preference',
        validate=validate.OneOf(ACCOUNT.ACCT_TYPES)))
    designation_preference = fields.List(field_for(
        CAOpenMeeting, 'designation_preference',
        validate=validate.OneOf(DESIG.DES_LEVEL_TYPES)))

    invitee_ids = fields.List(fields.Integer(), dump_only=True)
    _cached_contact_users = None  # while validating existence of users

    class Meta:
        model = CAOpenMeeting
        include_fk = True
        load_only = ('updated_by', 'account_id', 'created_by',
                     'external_participants')
        dump_only = default_exclude + (
            'updated_by', 'account_id', 'created_by', 'url', 'is_draft',
            'audio_filename', 'video_filename', 'cancelled', 'is_converted')
        exclude = ('participants', 'invitees')

    links = ma.Hyperlinks({
        'self': ma.URLFor(
            'corporate_access_api.caopenmeetingapi', row_id='<row_id>'),
        'collection': ma.URLFor(
            'corporate_access_api.caopenmeetinglistapi')
    }, dump_only=True)

    attachment_url = ma.Url(dump_only=True)

    event_type = ma.Nested(
        'app.corporate_access_resources.ref_event_types.schemas.'
        'CARefEventTypeSchema', only=['row_id', 'name'], dump_only=True)
    event_sub_type = ma.Nested(
        'app.corporate_access_resources.ref_event_sub_types.schemas.'
        'CARefEventSubTypeSchema', only=['row_id', 'name', 'has_slots'],
        dump_only=True)
    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True)
    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=creator_user_fields,
        dump_only=True)
    external_participants = ma.List(ma.Nested(
        'app.corporate_access_resources.ca_open_meeting_participants.'
        'schemas.CAOpenMeetingParticipantSchema',
        exclude=['participant_id'],
        only=['row_id', 'participant_email', 'participant_first_name',
              'participant_last_name', 'participant_designation',
              'sequence_id'], dump_only=True))
    invitees = ma.List(ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True))
    # joined_invitees = ma.List(ma.Nested(
    #     'app.resources.users.schemas.UserSchema', only=user_fields,
    #     dump_only=True))
    ca_open_meeting_participants = ma.List(ma.Nested(
        'app.corporate_access_resources.ca_open_meeting_participants.'
        'schemas.CAOpenMeetingParticipantSchema',
        exclude=['ca_open_meeting_id'],
        only=['ca_open_meeting_id', 'participant_id', 'row_id',
              'participant_email', 'participant_first_name',
              'participant_last_name', 'participant_designation',
              'sequence_id', 'participant']))
    slots = ma.List(ma.Nested(
        'app.corporate_access_resources.ca_open_meeting_slots.'
        'schemas.CAOpenMeetingSlotSchema', exclude=['event_id'],
        only=slot_fields))
    ca_open_meeting_invitees = ma.List(ma.Nested(
        'app.corporate_access_resources.ca_open_meeting_invitees.schemas.'
        'CAOpenMeetingInviteeSchema',
        only=['ca_open_meeting_id', 'invitee_id', 'row_id',
              'invitee', 'status']), dump_only=True)
    invited = ma.Nested(
        'app.corporate_access_resources.ca_open_meeting_invitees.schemas.'
        'CAOpenMeetingInviteeSchema', only=['row_id', 'invitee_id'],
        dump_only=True)

    @pre_dump(pass_many=True)
    def loads_urls(self, objs, many):
        """
        Loads the urls of invite_logo_url, invite_banner_url,
        audio_url, video_url
        """
        call_load = False  # minor optimisation
        if any(phfield in self.fields.keys() for phfield in [
                'attachment', 'attachment_url']):
            # call load urls only if the above fields are asked for
            call_load = True

        if many:  # #TODO: write optimized load_url here instead?
            for obj in objs:
                if call_load:
                    obj.load_urls()
        else:
            if call_load:
                objs.load_urls()
            objs.sort_participants_and_slots()

    @validates_schema
    def validate_started_at_and_ended_at(self, data):
        """
        Validate started_at and ended_at(ended_at greater then started_at)
        """
        error = False
        if ('started_at' in data and data['started_at'] and
                'ended_at' not in data):
            raise ValidationError(
                'Please provide end date', 'ended_at')
        elif ('ended_at' in data and data['ended_at'] and
                'started_at' not in data):
            raise ValidationError(
                'Please provide start date', 'started_at')
        elif ('started_at' in data and data['started_at'] and
                'ended_at' in data and data['ended_at']):
            if data['started_at'] > data['ended_at']:
                error = True

        if error:
            raise ValidationError(
                'End date should be greater than Start date',
                'started_at, ended_at')

    @validates_schema(pass_original=True)
    def validate_event_sub_type_for_event_type(self, data, original_data):
        """
        Validate event sub type according event type
        """
        error = False
        if ('event_type_id' in original_data and
                original_data['event_type_id'] and
                'event_sub_type_id' in original_data and
                original_data['event_sub_type_id']):
            event_sub_types = CARefEventSubType.query.filter(
                CARefEventSubType.event_type_id == original_data[
                    'event_type_id']).all()

            event_sub_type_ids = [
                sub_type.row_id for sub_type in event_sub_types]

            if (int(original_data['event_sub_type_id']) not in
                    event_sub_type_ids):
                error = True

        if error:
            raise ValidationError(
                'Event_sub_type_id: %(sub_id)s not exists in '
                'Event_type_id: %(type_id)s' % {'sub_id': original_data[
                    'event_sub_type_id'],
                    'type_id': original_data['event_type_id']},
                'event_sub_type_id')

    @validates_schema(pass_original=True)
    def validate_participant_invitee_file_ids(self, data, original_data):
        """
        Validate the participant_ids and invitee_ids, file_ids exist
        """
        error_part = False  # flag for participant_ids error
        error_invt = False  # flag for invitee_ids error
        missing_part = []  # list for invalid participant_ids
        missing_invt = []  # list for invalid invitee_ids
        self._cached_contact_users = []  # for invitee_ids valid user
        eids_part = []  # for participants
        eids_invt = []  # for invitees
        if ('ca_open_meeting_participants' in original_data and
                original_data['ca_open_meeting_participants']):
            caevent_paricipants = \
                original_data['ca_open_meeting_participants'][:]
            eids_part = [participate['participant_id'] for participate in
                         caevent_paricipants]
        if eids_part:
            # make query
            iids = []  # list for final id
            iids_part = []  # list for participant ids
            # for participant_ids
            for iid in eids_part:
                try:
                    iids_part.append(int(iid))
                except Exception as e:
                    continue
            iids = iids_part
            # if event created by group account user so host and participant
            # will be both account team member(child or group)
            user_data = User.query.filter(and_(
                User.row_id.in_(iids), or_(
                    User.account_id == g.current_user['primary_account_id'],
                    User.account_id == g.current_user['account_id']))).options(
                load_only('row_id', 'account_id')).all()
            participant_ids = []
            if user_data:
                for usr in user_data:
                    if usr.row_id in iids_part:
                        participant_ids.append(usr.row_id)

            missing_part = set(iids_part) - set(participant_ids)
            if missing_part:
                error_part = True

        if error_part:
            raise ValidationError(
                'User: %s do not exist' % missing_part,
                'participant_ids'
            )

        if 'invitee_ids' in original_data and original_data['invitee_ids']:
            eids_invt = original_data['invitee_ids'][:]

        if eids_invt:
            # make query
            iids_invt = []
            for iid in eids_invt:
                try:
                    iids_invt.append(int(iid))
                except Exception as e:
                    continue

            query = User.query.filter(
                User.row_id.in_(iids_invt),
                User.account_type != g.current_user['account_type']).options(
                load_only('row_id', 'account_id'))
            invitee_ids = []  # for validating missing (incorrect user ids)
            for c in query.all():
                if c.row_id in iids_invt:
                    invitee_ids.append(c.row_id)
                    self._cached_contact_users.append(c)
            missing_invt = set(iids_invt) - set(invitee_ids)
            if missing_invt:
                error_invt = True

        if error_invt:
            raise ValidationError(
                'User: %s do not exist' % missing_invt,
                'invitee_ids'
            )

    @validates_schema
    def validate_open_to_all_meeting_preferences(self, data):
        """
        Validate open to all meetings for account_type preferences and
        designation preferences
        """
        error = False
        if 'open_to_all' in data and data['open_to_all']:
            if ('account_type_preference' not in data or
                    'designation_preference' not in data):
                error = True

        else:
            if ('account_type_preference' in data or
                    'designation_preference' in data):
                raise ValidationError(
                    'If event is not open_to_all then ' +
                    'account_type_preference or designation_preference ' +
                    'can not be given',
                    'open_to_all, account_type_preference, ' +
                    'designation_preference')

        if error:
            raise ValidationError(
                'If event is open_to_all then account_type_preference ' +
                'and designation_preference must be given',
                'open_to_all, account_type_preference, designation_preference')


class CAOpenMeetingReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "Corporate Access Event" filters from request args
    """
    title = fields.String(load_only=True)
    # modified date fields
    started_at_from = fields.DateTime(load_only=True)
    started_at_to = fields.DateTime(load_only=True)
    ended_at_from = fields.DateTime(load_only=True)
    ended_at_to = fields.DateTime(load_only=True)

    event_type_id = fields.Integer(load_only=True)
    account_id = fields.Integer(load_only=True)
    event_sub_type_id = fields.Integer(load_only=True)
    main_filter = fields.String(load_only=True, validate=validate.OneOf(
        CAEVENT.CA_EVENT_LISTS))
    state_id = fields.Integer(load_only=True)
    city_id = fields.Integer(load_only=True)
    country_id = fields.Integer(load_only=True)
    city_name = fields.String(load_only=True)
    event_type_name = fields.String(load_only=True)
    event_sub_type_name = fields.String(load_only=True)
    cancelled = fields.String(load_only=True)
    account_type = fields.String(load_only=True)
    full_name = fields.String(load_only=True)
