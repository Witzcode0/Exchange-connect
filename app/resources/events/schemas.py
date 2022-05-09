"""
Schemas for "event" related models
"""

from marshmallow import (
    fields, validate, validates_schema, ValidationError, pre_dump)
from marshmallow_sqlalchemy import field_for
from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload, load_only
from flask import g

from app import ma
from app.base import constants as APP
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.resources.events import constants as EVENT
from app.resources.events.models import Event
from app.resources.event_invites import constants as EVENT_INVITE
from app.resources.contacts.models import Contact
from app.resources.users.models import User
from app.resources.users import constants as USER
from app.resources.event_file_library.models import EventLibraryFile


event_user_fields = user_fields + [
    # 'account.profile.profile_photo_url',
    'account.profile.profile_thumbnail_url', 'account.identifier']
event_invite_fields = ['row_id', 'status', 'links', 'rating', 'created_date',
                       'user_id', 'invitee']
event_user_fields.remove('profile.profile_photo_url')
event_user_fields.remove('profile.profile_thumbnail_url')


class EventSchema(ma.ModelSchema):
    """
    Schema for loading "Event" from request, and also formatting output
    """

    company_name = field_for(Event, 'company_name', validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=EVENT.COMPANY_NAME_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    subject = field_for(Event, 'subject', validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=EVENT.SUBJECT_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    description = field_for(Event, 'description', validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=EVENT.DESCRIPTION_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    timezone = field_for(Event, 'timezone', validate=validate.OneOf(
        USER.ALL_TIMEZONES))
    language = field_for(Event, 'language', validate=validate.OneOf(
        EVENT.EVENT_LANGUAGE_TYPES))
    contact_email = field_for(Event, 'contact_email',
                              field_class=fields.Email)
    dial_in_details = field_for(
        Event, 'dial_in_details', validate=[validate.Length(
            min=1, error=APP.MSG_NON_EMPTY), validate.Length(
            max=EVENT.DIALINDETAILS_MAX_LENGTH, error=APP.MSG_LENGTH_EXCEEDS)])
    file_ids = fields.List(fields.Integer(), dump_only=True)
    invitee_ids = fields.List(fields.Integer(), dump_only=True)
    _cached_contact_users = None  # while validating existence of users

    class Meta:
        model = Event
        include_fk = True
        load_only = ('deleted', 'updated_by', 'created_by', 'account_id')
        dump_only = default_exclude + (
            'updated_by', 'deleted', 'created_by', 'account_id')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.eventapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.eventslistapi')
    }, dump_only=True)
    # counts of participated, not participated
    participated = fields.Integer(dump_only=True)
    not_participated = fields.Integer(dump_only=True)
    maybe_participated = fields.Integer(dump_only=True)
    attended_participated = fields.Integer(dump_only=True)
    avg_rating = fields.Integer(dump_only=True)

    event_type = ma.Nested(
        'app.resources.event_types.schemas.EventTypeSchema',
        only=['name', 'row_id'], dump_only=True)
    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=event_user_fields,
        dump_only=True)
    editor = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=event_user_fields,
        dump_only=True)
    invites = ma.List(ma.Nested(
        'app.resources.event_invites.schemas.EventInviteSchema',
        only=event_invite_fields, dump_only=True))
    invited = ma.Nested(
        'app.resources.event_invites.schemas.EventInviteSchema',
        only=['row_id', 'user_id', 'rating'], dump_only=True)
    # add event invites nested field
    invitees = ma.List(ma.Nested(
        'app.resources.users.schemas.UserSchema', only=event_user_fields,
        dump_only=True))
    participants = ma.List(ma.Nested(
        'app.resources.users.schemas.UserSchema', only=event_user_fields,
        dump_only=True))
    non_participants = ma.List(ma.Nested(
        'app.resources.users.schemas.UserSchema', only=event_user_fields,
        dump_only=True))
    maybe_participants = ma.List(ma.Nested(
        'app.resources.users.schemas.UserSchema', only=event_user_fields,
        dump_only=True))
    attended_participants = ma.List(ma.Nested(
        'app.resources.users.schemas.UserSchema', only=event_user_fields,
        dump_only=True))
    files = ma.List(ma.Nested(
        'app.resources.event_file_library.schemas.EventLibraryFileSchema',
        only=['row_id', 'filename', 'file_type', 'file_url', 'thumbnail_url']))
    event_bookmarked = ma.Nested(
        'app.resources.event_bookmarks.schemas.EventBookmarkSchema',
        only=['row_id', 'links'], dump_only=True)

    @validates_schema(pass_original=True)
    def validate_invitee_ids(self, data, original_data):
        """
        Validate that the invitee_ids users (contacts) exist, and are contacts,
        these can be passed as part of event
        """
        error = False
        missing = []
        self._cached_contact_users = []
        eids = []
        if isinstance(self, AdminEventSchema):
            user_check_id = original_data['created_by']
        else:
            user_check_id = g.current_user['row_id']
        if 'invitee_ids' in original_data and original_data['invitee_ids']:
            eids = original_data['invitee_ids'][:]
        # validate user_ids, and load all the _cached_contact_users
        if eids:
            # make query
            iids = []
            for iid in eids:
                try:
                    iids.append(int(iid))
                except Exception as e:
                    continue
            query = Contact.query.filter(or_(
                and_(Contact.sent_by.in_(iids), Contact.sent_to ==
                     user_check_id),
                and_(Contact.sent_to.in_(iids), Contact.sent_by ==
                     user_check_id))).options(
                # sendee and related stuff
                joinedload(Contact.sendee).load_only('row_id').joinedload(
                    User.profile),
                # sender and related stuff
                joinedload(Contact.sender).load_only('row_id').joinedload(
                    User.profile))
            invitee_ids = []  # for validating missing (incorrect user ids)
            for c in query.all():
                the_contact = c.sender if c.sent_to ==\
                    user_check_id else c.sendee
                self._cached_contact_users.append(the_contact)
                invitee_ids.append(the_contact.row_id)

            missing = set(iids) - set(invitee_ids)
            if missing:
                error = True

        if error:
            raise ValidationError(
                'Contacts: %s do not exist' % missing,
                'invitee_ids'
            )

    @validates_schema(pass_original=True)
    def validate_file_ids(self, data, original_data):
        """
        Validate that the file_ids "event library file" exist
        """
        error = False
        missing = []
        self._cached_files = []
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
            self._cached_files = [f for f in EventLibraryFile.query.filter(
                EventLibraryFile.row_id.in_(fids)).options(load_only(
                    'row_id', 'deleted')).all() if not f.deleted]
            file_ids = [f.row_id for f in self._cached_files]
            missing = set(fids) - set(file_ids)
            if missing:
                error = True

        if error:
            raise ValidationError(
                'Files: %s do not exist' % missing,
                'file_ids'
            )

    @validates_schema(pass_original=True)
    def validate_event_type(self, data, original_data):
        """
        Validate if open_to_all and public_event are not true at same time
        """
        error = False
        if 'public_event' in original_data and 'open_to_all' in original_data:
            if original_data['public_event'] and original_data['open_to_all']:
                error = True

        if error:
            raise ValidationError(
                "Event cannot be both public event and open to all"
            )

    @pre_dump(pass_many=True)
    def loads_counts(self, objs, many, load_invite=True):
        """
        Loads the counts of participated, not participated and also
        get event invite row_id
        """
        call_load = False  # minor optimisation
        if any(phfield in self.fields.keys() for phfield in ['invited']):
            # call load urls only if the above fields are asked for
            call_load = True

        if many:
            if call_load:
                for obj in objs:
                    if load_invite:
                        for event_invite_data in obj.invites:
                            if (event_invite_data.user_id ==
                                    g.current_user['row_id']):
                                obj.invited = event_invite_data
                                break
        else:
            if call_load:
                if load_invite:
                    for event_invite_data in objs.invites:
                        if event_invite_data.user_id == g.current_user[
                                'row_id']:
                            objs.invited = event_invite_data
                            break


class AdminEventSchema(EventSchema):
    """
    Schema for loading "Event" for Admin from request,
    and also formatting output
    """

    class Meta:
        model = Event
        include_fk = True
        load_only = ('deleted', 'updated_by')
        dump_only = default_exclude + ('updated_by', 'deleted')

    @pre_dump(pass_many=True)
    def loads_counts(self, objs, many, load_invite=False):
        """
        Loads the counts of participated, not participated and also
        get event invite row_id
        """
        super(AdminEventSchema, self).loads_counts(
            objs, many, load_invite=load_invite)


class EventReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "Event" filters from request args
    """
    # standard db fields

    event_type_id = fields.Integer(load_only=True)
    main_filter = fields.String(load_only=True, validate=validate.OneOf(
        EVENT.EVENT_LISTS))

    place = fields.String(load_only=True)
    company_name = fields.String(load_only=True)
    subject = fields.String(load_only=True)
    description = fields.String(load_only=True)

    # special participant ids field
    invitee_ids = fields.List(fields.Integer(), load_only=True)

    updated_by = fields.Integer(load_only=True)
    created_by = fields.Integer(load_only=True)

    # modified date fields
    start_date_from = fields.DateTime(load_only=True)
    start_date_to = fields.DateTime(load_only=True)
    end_date_from = fields.DateTime(load_only=True)
    end_date_to = fields.DateTime(load_only=True)


class AdminEventReadArgsSchema(EventReadArgsSchema):
    """
    Schema for reading "AdminEvent" filters from request args
    """
    account_id = fields.Integer(load_only=True)
