"""
Schemas for "webcast" related models
"""

from marshmallow import (
    fields, validate, pre_dump, validates_schema, ValidationError, pre_load)
from sqlalchemy.orm import load_only, joinedload
from sqlalchemy import and_, or_
from marshmallow_sqlalchemy import field_for
from flask import g

from app import ma
from app.base.schemas import (default_exclude, BaseReadArgsSchema,
                              user_fields)
from app.base import constants as APP
from app.webcast_resources.webcasts.models import Webcast
from app.webcast_resources.webcasts import constants as WEBCAST
from app.resources.users.models import User
from app.resources.contacts.models import Contact
from app.resources.file_archives.models import ArchiveFile
from app.resources.contact_requests.models import ContactRequest


# account details that will be passed while populating account relation
account_fields = ['row_id', 'links', 'account_name', 'account_type']

# account details that will be passed while populating account relation
creator_user_fields = user_fields + ['account.profile.profile_thumbnail_url']


class WebcastSchema(ma.ModelSchema):
    """
    Schema for loading "webcast" from request,
    and also formatting output
    """

    # default fields to exclude from the schema for speed up
    # webcast_hosts is being used for getlist views
    _default_exclude_fields = ['webcast_settings', 'webcast_questions',
                               'webcast_attendee', 'webcast_answers',
                               'notifications', 'external_hosts',
                               'external_invitees', 'hosts',
                               'webcast_invitees', 'files', 'invitees',
                               'participants']

    title = field_for(Webcast, 'title', validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=WEBCAST.COMMAN_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    description = field_for(Webcast, 'description', validate=[
        validate.Length(max=WEBCAST.DESCRIPTION_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    file_ids = fields.List(fields.Integer(), dump_only=True)
    host_ids = fields.List(fields.Integer(), dump_only=True)
    cc_emails = fields.List(fields.Email(), allow_none=True)
    _cached_host_users = None  # while validating existence of user
    invitee_ids = fields.List(fields.Integer(), dump_only=True)
    _cached_contact_users = None  # while validating existence of users
    _cached_files = None
    stats = ma.Nested('app.webcast_resources.webcast_stats.schemas.'
                      'WebcastStatsSchema', exclude=['webcast_id', 'webcast'],
                      dump_only=True)

    class Meta:
        model = Webcast
        include_fk = True
        load_only = ('updated_by', 'account_id', 'created_by',
                     'external_participants')
        dump_only = default_exclude + (
            'updated_by', 'account_id', 'created_by', 'is_draft',
            'audio_filename', 'video_filename', 'cancelled', 'presenter_url',
            'admin_url')
        exclude = ('conference_id',)

    links = ma.Hyperlinks({
        'self': ma.URLFor(
            'webcast_api.webcastapi', row_id='<row_id>'),
        'collection': ma.URLFor('webcast_api.webcastlistapi')
    }, dump_only=True)

    invite_logo_url = ma.Url(dump_only=True)
    invite_banner_url = ma.Url(dump_only=True)
    audio_url = ma.Url(dump_only=True)
    video_url = ma.Url(dump_only=True)

    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True)
    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=creator_user_fields,
        dump_only=True)
    hosts = ma.List(ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True))
    participants = ma.List(ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True))
    invitees = ma.List(ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True))
    invited = ma.Nested(
        'app.webcast_resources.webcast_invitees.schemas.WebcastInviteeSchema',
        only=['webcast_id', 'invitee_id', 'row_id', 'status',
              'conference_url'], dump_only=True)
    webcast_participants = ma.List(ma.Nested(
        'app.webcast_resources.webcast_participants.'
        'schemas.WebcastParticipantSchema', exclude=['webcast_id'],
        only=['webcast_id', 'participant_id', 'row_id', 'sequence_id',
              'participant_email', 'participant_designation',
              'participant_first_name', 'participant_last_name',
              'participant', 'conference_url','is_mail_sent','email_status']))
    webcast_hosts = ma.List(ma.Nested(
        'app.webcast_resources.webcast_hosts.schemas.WebcastHostSchema',
        only=['webcast_id', 'host_id', 'row_id', 'host_email',
              'host_designation', 'host_first_name', 'host_last_name', 'host',
              'conference_url', 'is_mail_sent', 'email_status'],
        dump_only=True))
    webcast_invitees = ma.List(ma.Nested(
        'app.webcast_resources.webcast_invitees.schemas.WebcastInviteeSchema',
        only=['webcast_id', 'invitee_id', 'row_id', 'invitee_email',
              'invitee_designation', 'invitee_first_name', 'invitee_last_name',
              'invitee', 'conference_url', 'status', 'is_mail_sent',
              'email_status', 'crm_group', 'user_id'], dump_only=True))
    external_invitees = ma.List(ma.Nested(
        'app.webcast_resources.webcast_invitees.'
        'schemas.WebcastInviteeSchema', exclude=['invitee_id'],
        only=['row_id', 'invitee_email', 'invitee_designation',
              'invitee_first_name', 'invitee_last_name']))
    external_hosts = ma.List(ma.Nested(
        'app.webcast_resources.webcast_hosts.'
        'schemas.WebcastHostSchema', exclude=['invitee_id'],
        only=['row_id', 'host_email', 'host_designation',
              'host_first_name', 'host_last_name']))
    external_participants = ma.List(ma.Nested(
        'app.webcast_resources.webcast_participants.'
        'schemas.WebcastParticipantSchema', exclude=['invitee_id'],
        only=['row_id', 'participant_email', 'participant_designation',
              'participant_first_name', 'participant_last_name',
              'sequence_id']))
    rsvps = ma.List(ma.Nested(
        'app.webcast_resources.webcast_rsvps.schemas.WebcastRSVPSchema',
        only=['row_id', 'phone', 'contact_person', 'email', 'sequence_id',
              'conference_url', 'is_mail_sent', 'email_status']))
    files = ma.List(ma.Nested(
        'app.resources.file_archives.schemas.ArchiveFileSchema',
        only=['row_id', 'filename', 'file_type', 'file_major_type',
              'file_url', 'thumbnail_url']), dump_only=True)

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
                'audio_url', 'audio_filename', 'video_url', 'video_filename']):
            # call load urls only if the above fields are asked for
            call_load = True

        if many:  # #TODO: write optimized load_url here instead?
            for obj in objs:
                if call_load:
                    obj.load_urls()
        else:
            if call_load:
                objs.load_urls()

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
    def validate_participant_host_invitee_file_ids(self, data, original_data):
        """
        Validate the participant_ids, host_ids and invitee_ids, file_ids  exist
        """
        error_part = False  # flag for participant_ids error
        error_host = False  # flag for host_ids error
        error_invt = False  # flag for invitee_ids error
        missing_host = []  # list for invalid host_ids
        missing_invt = []  # list for invalid invitee_ids
        self._cached_host_users = []  # for host_ids valid valid user
        self._cached_contact_users = []  # for invitee_ids valid user
        eids_part = []  # for participants
        eids_host = []  # for hosts
        eids_invt = []  # for invitees
        if ('webcast_participants' in original_data and
                original_data['webcast_participants']):
            webcast_paricipants = original_data['webcast_participants'][:]
            eids_part = [participate['participant_id'] for participate in
                         webcast_paricipants]
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
            invitee_ids = []  # for validating missing (incorrect user ids)
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
                         ContactRequest.sent_by == g.current_user['row_id']))
                ).options(
                    # sendee and related stuff
                    joinedload(ContactRequest.sendee).load_only('row_id'). \
                        joinedload(User.profile),
                    # sender and related stuff
                    joinedload(ContactRequest.sender).load_only('row_id'). \
                        joinedload(User.profile)
                )

                for c in query.all():
                    the_contact = c.sender if c.sent_to == \
                                              g.current_user[
                                                  'row_id'] else c.sendee
                    ## Todo : Need to decide whether to check a/c type or not
                    # if (the_contact.account.account_type !=
                    #         g.current_user['account_type']):
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

    @pre_load(pass_many=True)
    def cc_emails_none_conversion(self, objs, many):
        """
        convert cc_emails into None if empty list and Null
        """
        if 'cc_emails' in objs and (
                '' in objs['cc_emails'] or '[]' in objs['cc_emails']):
            objs['cc_emails'] = None


class WebcastReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "webcast" filters from request args
    """
    title = fields.String(load_only=True)
    description = fields.String(load_only=True)
    url = fields.String(load_only=True)
    is_draft = fields.String(load_only=True)
    cancelled = fields.String(load_only=True)
    # modified date fields
    started_at_from = fields.DateTime(load_only=True)
    started_at_to = fields.DateTime(load_only=True)
    ended_at_from = fields.DateTime(load_only=True)
    ended_at_to = fields.DateTime(load_only=True)
    main_filter = fields.String(load_only=True, validate=validate.OneOf(
        WEBCAST.WEBCAST_LISTS))
