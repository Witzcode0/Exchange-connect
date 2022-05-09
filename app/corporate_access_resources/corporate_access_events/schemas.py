"""
Schemas for "corporate access events" related models
"""

from marshmallow import (
    fields, validate, pre_dump, validates_schema, ValidationError, pre_load)
from marshmallow_sqlalchemy import field_for
from sqlalchemy.orm import load_only, joinedload
from flask import g
from sqlalchemy import and_, or_

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.base import constants as APP
from app.corporate_access_resources.corporate_access_events.models import \
    CorporateAccessEvent
from app.corporate_access_resources.corporate_access_events import \
    constants as CAEVENT
from app.corporate_access_resources.ref_event_types.models import \
    CARefEventType
from app.corporate_access_resources.ref_event_sub_types.models import \
    CARefEventSubType
from app.resources.users.models import User
from app.resources.accounts.models import Account
from app.resources.contacts.models import Contact
from app.resources.file_archives.models import ArchiveFile
from app.resources.accounts import constants as ACC
from app.resources.contact_requests.models import ContactRequest


# account details that will be passed while populating account relation
account_fields = ['row_id', 'account_name', 'account_type']
# slot fields that will be passed while populating slot relation
slot_fields = ['row_id', 'started_at', 'ended_at', 'slot_type',
               'bookable_seats', 'booked_seats', 'address', 'event_id',
               'slot_name', 'text_1', 'text_2', 'available_seats', 'rejected',
               'corporate_access_event_inquiries', 'disallowed',
               'rejected_inquiries', 'description', 'inquired']

# account details that will be passed while populating account relation
creator_user_fields = user_fields + ['account.profile.profile_thumbnail_url']


class CorporateAccessEventSchema(ma.ModelSchema):
    """
    Schema for loading "Corporate Access Event" from request,
    and also formatting output
    """

    # default fields to exclude from the schema for speed up
    _default_exclude_fields = [
        'notifications', 'external_hosts', 'external_participants',
        'external_invitees', 'agendas', 'hosts', 'participants', 'invitees',
        'joined_invitees', 'corporate_access_event_participants',
        'corporate_access_event_hosts',
        'corporate_access_event_invitees', 'rsvps',
        'corporate_access_event_attendee', 'files', 'state', 'country',
        'corporate_access_event_inquiries', 'collaborators']

    title = field_for(CorporateAccessEvent, 'title', validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=CAEVENT.COMMON_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    description = field_for(CorporateAccessEvent, 'description', validate=[
        validate.Length(max=CAEVENT.DESCRIPTION_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    cc_emails = fields.List(fields.Email(), allow_none=True)

    account_type_preference = fields.List(field_for(
        CorporateAccessEvent, 'account_type_preference',
        validate=validate.OneOf(ACC.ACCT_TYPES)))

    file_ids = fields.List(fields.Integer(), dump_only=True)
    participant_company_ids = fields.List(fields.Integer(), dump_only=True)
    host_ids = fields.List(fields.Integer(), dump_only=True)
    _cached_host_users = None  # while validating existence of user
    invitee_ids = fields.List(fields.Integer(), dump_only=True)
    _cached_contact_users = None  # while validating existence of users
    _cached_files = None
    _cached_participant_companies = None
    _cached_event_type = None
    _cached_meeting_account = None
    _event_type = None  # only used in put time
    stats = (ma.Nested(
        'app.corporate_access_resources.corporate_access_event_stats.schemas.'
        'CorporateAccessEventStatsSchema', exclude=[
            'corporate_access_event_id', 'event'], dump_only=True))
    agendas = ma.List(ma.Nested(
        'app.corporate_access_resources.corporate_access_event_agendas.'
        'schemas.CorporateAccessEventAgendaSchema', exclude=[
            'corporate_access_event_id'], only=[
            'row_id', 'corporate_access_event_id', 'title', 'started_at',
            'ended_at', 'description', 'address', 'secondary_title']))
    # this is for one-to-one meeting event type
    meeting_company_id = fields.Integer(dump_only=True)

    class Meta:
        model = CorporateAccessEvent
        include_fk = True
        load_only = ('updated_by', 'account_id', 'created_by')
        dump_only = default_exclude + (
            'updated_by', 'account_id', 'created_by', 'url', 'is_draft',
            'audio_filename', 'video_filename', 'is_open_meeting')
        exclude = ('participants', )

    links = ma.Hyperlinks({
        'self': ma.URLFor(
            'corporate_access_api.corporateaccesseventapi', row_id='<row_id>'),
        'collection': ma.URLFor(
            'corporate_access_api.corporateaccesseventlistapi')
    }, dump_only=True)

    invite_logo_url = ma.Url(dump_only=True)
    invite_banner_url = ma.Url(dump_only=True)
    audio_url = ma.Url(dump_only=True)
    video_url = ma.Url(dump_only=True)
    transcript_url = ma.Url(dump_only=True)
    attachment_url = ma.Url(dump_only=True)

    event_type = ma.Nested(
        'app.corporate_access_resources.ref_event_types.schemas.'
        'CARefEventTypeSchema', only=['row_id', 'name', 'is_meeting'],
        dump_only=True)
    event_sub_type = ma.Nested(
        'app.corporate_access_resources.ref_event_sub_types.schemas.'
        'CARefEventSubTypeSchema', only=[
            'row_id', 'name', 'has_slots', 'show_time'], dump_only=True)
    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True)
    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=creator_user_fields,
        dump_only=True)
    hosts = ma.List(ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True))
    external_hosts = ma.List(ma.Nested(
        'app.corporate_access_resources.corporate_access_event_hosts.'
        'schemas.CorporateAccessEventHostSchema', exclude=['host_id'],
        only=['row_id', 'host_email', 'host_first_name', 'host_last_name',
              'host_designation']))
    participants = ma.List(ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True))
    external_participants = ma.List(ma.Nested(
        'app.corporate_access_resources.corporate_access_event_participants.'
        'schemas.CorporateAccessEventParticipantSchema',
        exclude=['participant_id'],
        only=['row_id', 'participant_email', 'participant_first_name',
              'participant_last_name', 'participant_designation',
              'sequence_id'], dump_only=True))
    invitees = ma.List(ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True))
    joined_invitees = ma.List(ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True))
    external_invitees = ma.List(ma.Nested(
        'app.corporate_access_resources.corporate_access_event_invitees.'
        'schemas.CorporateAccessEventInviteeSchema', exclude=['invitee_id'],
        only=['row_id', 'invitee_email', 'invitee_first_name',
              'invitee_last_name', 'invitee_designation']))
    corporate_access_event_participants = ma.List(ma.Nested(
        'app.corporate_access_resources.corporate_access_event_participants.'
        'schemas.CorporateAccessEventParticipantSchema',
        exclude=['corporate_access_event_id'],
        only=['corporate_access_event_id', 'participant_id', 'row_id',
              'participant_email', 'participant_first_name',
              'participant_last_name', 'participant_designation',
              'sequence_id', 'participant', 'is_mail_sent','email_status']))
    corporate_access_event_hosts = ma.List(ma.Nested(
        'app.corporate_access_resources.corporate_access_event_hosts.'
        'schemas.CorporateAccessEventHostSchema',
        only=['corporate_access_event_id', 'host_id', 'row_id', 'host_email',
              'host_first_name', 'host_last_name', 'host_designation',
              'is_mail_sent','email_status'], dump_only=True))
    slots = ma.List(ma.Nested(
        'app.corporate_access_resources.corporate_access_event_slots.'
        'schemas.CorporateAccessEventSlotSchema', exclude=['event_id'],
        only=slot_fields))
    corporate_access_event_invitees = ma.List(ma.Nested(
        'app.corporate_access_resources.corporate_access_event_invitees.'
        'schemas.CorporateAccessEventInviteeSchema',
        only=['corporate_access_event_id', 'invitee_id', 'row_id',
              'invitee_email', 'invitee_first_name', 'created_by',
              'invitee_last_name', 'invitee_designation', 'invitee', 'status',
              'user_id', 'invitee_remark', 'uninvited', 'is_mail_sent',
              'crm_group', 'email_status'], dump_only=True))
    invited = ma.Nested(
        'app.corporate_access_resources.corporate_access_event_invitees.'
        'schemas.CorporateAccessEventInviteeSchema',
        only=['corporate_access_event_id', 'invitee_id', 'row_id',
              'invitee_email', 'invitee_first_name',
              'invitee_last_name', 'invitee_designation', 'invitee', 'status',
              'uninvited', 'is_mail_sent', 'email_status'],
        dump_only=True)
    collaborated = ma.Nested(
        'app.corporate_access_resources.corporate_access_event_collaborators.'
        'schemas.CorporateAccessEventCollaboratorSchema',
        only=['row_id'], dump_only=True)
    hosted = ma.Nested(
        'app.corporate_access_resources.corporate_access_event_hosts.'
        'schemas.CorporateAccessEventHostSchema',
        only=['row_id'],
        dump_only=True)
    participated = ma.Nested(
        'app.corporate_access_resources.corporate_access_event_participants.'
        'schemas.CorporateAccessEventParticipantSchema',
        only=['row_id'],
        dump_only=True)
    rsvped = ma.Nested(
        'app.corporate_access_resources.corporate_access_event_rsvps.'
        'schemas.CorporateAccessEventRSVPSchema',
        only=['row_id'],
        dump_only=True)
    rsvps = ma.List(ma.Nested(
        'app.corporate_access_resources.corporate_access_event_rsvps.'
        'schemas.CorporateAccessEventRSVPSchema',
        only=['row_id', 'phone', 'contact_person', 'email', 'creator',
              'sequence_id', 'is_mail_sent','email_status']))
    collaborators = ma.List(ma.Nested(
        'app.corporate_access_resources.corporate_access_event_collaborators.'
        'schemas.CorporateAccessEventCollaboratorSchema',
        exclude=['corporate_access_event_id'],
        only=['row_id', 'collaborator_id', 'permissions', 'collaborator',
              'is_mail_sent','email_status']))

    corporate_access_event_attendee = ma.List(ma.Nested(
        'app.corporate_access_resources.corporate_access_event_attendees.'
        'schemas.CorporateAccessEventAttendeeSchema', only=[
            'row_id', 'rating', 'attendee_id', 'comment', 'guest_invitee'],
        dump_only=True))
    files = ma.List(ma.Nested(
        'app.resources.file_archives.schemas.ArchiveFileSchema',
        only=['row_id', 'filename', 'file_type', 'file_major_type',
              'file_url', 'thumbnail_url']), dump_only=True)
    caevent_participant_companies = ma.List(ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True))

    @pre_dump(pass_many=True)
    def loads_urls(self, objs, many):
        """
        Loads the urls of invite_logo_url, invite_banner_url,
        audio_url, video_url
        """
        call_load = False  # minor optimisation
        if any(phfield in self.fields.keys() for phfield in [
                'invite_logo_url', 'invite_logo_filename',
                'invite_banner_url', 'invite_banner_filename',
                'audio_url', 'audio_filename', 'video_url', 'video_filename',
                'attachment', 'attachment_url', 'transcript_url']):
            # call load urls only if the above fields are asked for
            call_load = True

        if many:  # #TODO: write optimized load_url here instead?
            for obj in objs:
                if call_load:
                    obj.load_urls()
        else:
            if call_load:
                objs.load_urls()
            objs.sort_rsvps_and_participants()

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
    def validate_participant_host_invitee_file_company_ids(
            self, data, original_data):
        """
        Validate the participant_ids, host_ids and invitee_ids, file_ids exist
        """
        error_part = False  # flag for participant_ids error
        error_host = False  # flag for host_ids error
        error_invt = False  # flag for invitee_ids error
        missing_part = []  # list for invalid participant_ids
        missing_host = []  # list for invalid host_ids
        missing_invt = []  # list for invalid invitee_ids
        self._cached_host_users = []  # for host_ids valid valid user
        self._cached_contact_users = []  # for invitee_ids valid user
        eids_part = []  # for participants
        eids_host = []  # for hosts
        eids_invt = []  # for invitees
        self._cached_event_type = None
        self._cached_meeting_account = None
        # for one-to-one meeting
        if self._event_type:
            self._cached_event_type = self._event_type
        if (not self._event_type and 'event_type_id' in original_data and
                original_data['event_type_id']):
            self._cached_event_type = CARefEventType.query.get(
                original_data['event_type_id'])
        # event_type is meeting
        if (self._cached_event_type.is_meeting and
                'meeting_company_id' in original_data and
                original_data['meeting_company_id']):
            self._cached_meeting_account = Account.query.get(
                original_data['meeting_company_id'])
            # if meeting company is not exists
            if not self._cached_meeting_account:
                raise ValidationError(
                    'Account: %s do not exist' % original_data[
                        'meeting_company_id'], 'meeting_company_id')

        # participants company exists or not
        self._cached_participant_companies = []
        missing_companies = []
        error_companies = False
        # load all the participants companies
        cp_ids = []
        if 'participant_company_ids' in original_data and original_data[
                'participant_company_ids']:
            cp_ids = original_data['participant_company_ids'][:]
        # validate company_ids, and load all the _cached_companies
        if cp_ids:
            # make query
            cpids = []
            for cp in cp_ids:
                try:
                    cpids.append(int(cp))
                except Exception as e:
                    continue
            self._cached_participant_companies = [
                f for f in Account.query.filter(
                    Account.row_id.in_(cpids)).options(load_only(
                        'row_id', 'deleted')).all() if not f.deleted]
            participant_company_ids = [
                f.row_id for f in self._cached_participant_companies]
            missing_companies = set(cpids) - set(participant_company_ids)
            if missing_companies:
                error_companies = True

        if error_companies:
            raise ValidationError(
                'Participant Companies: %s do not exist' % missing_companies,
                'participant_company_ids'
            )

        if ('corporate_access_event_participants' in original_data and
                original_data['corporate_access_event_participants']):
            caevent_paricipants = \
                original_data['corporate_access_event_participants'][:]
            eids_part = [participate['participant_id'] for participate in
                         caevent_paricipants]
        if 'host_ids' in original_data and original_data['host_ids']:
            eids_host = original_data['host_ids'][:]
        if eids_part or eids_host:
            # make query
            iids = []  # list for final id
            iids_part = []  # list for participant ids
            iids_host = []  # list for host ids
            # for participant_ids
            for iid in eids_part:
                try:
                    iids_part.append(int(iid))
                except Exception as e:
                    continue
            # for host_ids
            for iid in eids_host:
                try:
                    iids_host.append(int(iid))
                except Exception as e:
                    continue
            iids = iids_part + iids_host
            # if event created by group account user so host and participant
            # will be both account team member(child or group)
            user_data = User.query.filter(and_(
                User.row_id.in_(iids), or_(
                    User.account_id == g.current_user['primary_account_id'],
                    User.account_id == g.current_user['account_id']))).options(
                load_only('row_id', 'account_id')).all()
            participant_ids = []
            host_ids = []
            if user_data:
                for usr in user_data:
                    if usr.row_id in iids_host:
                        host_ids.append(usr.row_id)
                        self._cached_host_users.append(usr)
                    if usr.row_id in iids_part:
                        participant_ids.append(usr.row_id)

            missing_host = set(iids_host) - set(host_ids)
            if missing_host:
                error_host = True
            missing_part = set(iids_part) - set(participant_ids)
            if missing_part:
                error_part = True

        if error_part:
            raise ValidationError(
                'User: %s do not exist' % missing_part,
                'participant_ids'
            )
        if error_host:
            raise ValidationError(
                'User: %s do not exist' % missing_host,
                'host_ids'
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
            invitee_ids = []  # for validating missing (incorrect user ids)
            if (self._cached_event_type.is_meeting and
                    self._cached_meeting_account):
                query = User.query.filter(and_(
                    User.row_id.in_(iids_invt),
                    User.account_id == self._cached_meeting_account.row_id))
                for c in query.all():
                    self._cached_contact_users.append(c)
                    invitee_ids.append(c.row_id)
            else:
                query = Contact.query.filter(or_(
                    and_(Contact.sent_by.in_(iids_invt), Contact.sent_to ==
                         g.current_user['row_id']),
                    and_(Contact.sent_to.in_(iids_invt), Contact.sent_by ==
                         g.current_user['row_id']))).options(
                    # sendee and related stuff
                    joinedload(Contact.sendee).load_only('row_id').joinedload(
                        User.profile),
                    # sender and related stuff
                    joinedload(Contact.sender).load_only('row_id').joinedload(
                        User.profile))

                for c in query.all():
                    the_contact = c.sender if c.sent_to == \
                        g.current_user['row_id'] else c.sendee
                    self._cached_contact_users.append(the_contact)
                    invitee_ids.append(the_contact.row_id)

                remaining_iids_invt = set(iids_invt) - set(invitee_ids)
                if remaining_iids_invt:
                    query = ContactRequest.query.filter(or_(
                        and_(ContactRequest.sent_by.in_(remaining_iids_invt),
                             ContactRequest.sent_to == g.current_user['row_id']),
                        and_(ContactRequest.sent_to.in_(remaining_iids_invt),
                             ContactRequest.sent_by ==g.current_user['row_id']))
                        ).options(
                            # sendee and related stuff
                            joinedload(ContactRequest.sendee).load_only('row_id').\
                                joinedload(User.profile),
                            # sender and related stuff
                            joinedload(ContactRequest.sender).load_only('row_id').\
                                joinedload(User.profile)
                        )

                    for c in query.all():
                        the_contact = c.sender if c.sent_to == \
                                                  g.current_user[
                                                      'row_id'] else c.sendee
                        if (the_contact.account.account_type !=
                                g.current_user['account_type']):
                            self._cached_contact_users.append(the_contact)
                            invitee_ids.append(the_contact.row_id)

            missing_invt = set(iids_invt) - set(invitee_ids)
            if missing_invt:
                error_invt = True

        if error_invt:
            raise ValidationError(
                'Contacts: %s do not exist' % missing_invt,
                'invitee_ids'
            )

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

    @validates_schema(pass_original=True)
    def validate_has_slot_type_validation(self, data, original_data):
        """
        Validate non has_slots type to not create slots in event
        """
        error = False
        if 'event_type_id' in data and data[
                'event_type_id'] and 'event_sub_type_id' in data and data[
                'event_sub_type_id'] and 'slots' in data and data['slots']:
            event_type = CARefEventSubType.query.filter(and_(
                CARefEventSubType.event_type_id == data['event_type_id'],
                CARefEventSubType.row_id == data['event_sub_type_id'])).first()

            if not event_type.has_slots:
                error = True

        if error:
            raise ValidationError('Event sub type is not has_slot, '
                                  'so you can not add slots', 'slots')

    @pre_load(pass_many=True)
    def cc_emails_none_conversion(self, objs, many):
        """
        convert cc_emails into None if empty list and Null
        """
        if 'cc_emails' in objs and (
                '' in objs['cc_emails'] or '[]' in objs['cc_emails']):
            objs['cc_emails'] = None

        if 'account_type_preference' in objs and (
                '' in objs['account_type_preference'] or '[]' in objs[
                    'account_type_preference']):
            objs['account_type_preference'] = []
        if 'open_to_all' in objs and not eval(
                objs['open_to_all'].capitalize()):
            objs['account_type_preference'] = []

    @validates_schema
    def validate_open_to_all_event_preferences(self, data):
        """
        Validate open to all meetings for account_type preferences and
        designation preferences
        """
        error = False
        if 'open_to_all' in data and data['open_to_all']:
            if 'account_type_preference' not in data:
                error = True

        else:
            if 'account_type_preference' in data and data[
                    'account_type_preference']:
                raise ValidationError(
                    'If event is not open_to_all then ' +
                    'account_type_preference can not be given',
                    'open_to_all, account_type_preference')

        if error:
            raise ValidationError(
                'If event is open_to_all then account_type_preference must be '
                'given', 'open_to_all, account_type_preference')


class AdminCorporateAccessEventSchema(CorporateAccessEventSchema):
    """
    Schema for loading "Corporate Access Event" from post request,
    and also formatting output for admin only
    """

    class Meta:
        model = CorporateAccessEvent
        include_fk = True
        load_only = ('updated_by', 'created_by')
        dump_only = default_exclude + (
            'updated_by', 'created_by', 'url', 'is_draft',
            'audio_filename', 'video_filename', 'is_open_meeting')
        exclude = ('participants', )


class CorporateAccessEventEditSchema(CorporateAccessEventSchema):
    """
    Schema for loading "Corporate Access Event" from put request,
    and also formatting output
    """

    class Meta:
        model = CorporateAccessEvent
        dump_only = default_exclude + (
            'updated_by', 'account_id', 'created_by', 'url', 'is_draft',
            'audio_filename', 'video_filename', 'event_type_id',
            'event_sub_type_id', 'transcript_filename')


class CorporateAccessEventReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "Corporate Access Event" filters from request args
    """
    title = fields.String(load_only=True)
    description = fields.String(load_only=True)
    url = fields.String(load_only=True)
    is_draft = fields.String(load_only=True)
    account_id = fields.String(load_only=True)
    cancelled = fields.String(load_only=True)
    # modified date fields
    started_at_from = fields.DateTime(load_only=True)
    started_at_to = fields.DateTime(load_only=True)
    ended_at_from = fields.DateTime(load_only=True)
    ended_at_to = fields.DateTime(load_only=True)

    event_type_id = fields.Integer(load_only=True)
    event_sub_type_id = fields.Integer(load_only=True)
    event_type_name = fields.String(load_only=True)
    main_filter = fields.String(load_only=True, validate=validate.OneOf(
        CAEVENT.CA_EVENT_LISTS))
    state_id = fields.Integer(load_only=True)
    city_id = fields.Integer(load_only=True)
    country_id = fields.Integer(load_only=True)
    city = fields.String(load_only=True)
    state = fields.String(load_only=True)
    country = fields.String(load_only=True)
    open_to_all = fields.Boolean(load_only=True)
    company_name = fields.String(load_only=True)


class CorporateAccessNoAuthSchema(ma.ModelSchema):

    _include_only = [
        'row_id', 'open_to_all', 'account_id', 'title','started_at',
        'ended_at', 'url', 'audio_filename', 'video_filename',
        'transcript_filename']
    class Meta:
        model = CorporateAccessEvent
        include_fk = True
        load_only = ('updated_by', 'account_id', 'created_by')
        dump_only = default_exclude + (
            'updated_by', 'account_id', 'created_by', 'url', 'is_draft',
            'audio_filename', 'video_filename', 'is_open_meeting')
        exclude = ('participants', )

    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True)
