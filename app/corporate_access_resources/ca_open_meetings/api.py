"""
API endpoints for "ca open meetings" package.
"""

from datetime import datetime as dt

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g, json
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import load_only, joinedload, contains_eager
from sqlalchemy import and_, or_, func, any_
from flasgger.utils import swag_from

from app import db, c_abort, caopenmeetingattachmentfile
from app.base.api import AuthResource
from app.base import constants as APP
from app.corporate_access_resources.corporate_access_events import \
    constants as CAEVENT
from app.common.helpers import store_file, copy_file
from app.corporate_access_resources.ca_open_meetings.models \
    import CAOpenMeeting
from app.corporate_access_resources.ca_open_meetings.schemas import (
    CAOpenMeetingSchema, CAOpenMeetingReadArgsSchema)
from app.corporate_access_resources.ca_open_meetings.helpers import (
    remove_unused_data)
from app.corporate_access_resources.ca_open_meeting_participants.models \
    import CAOpenMeetingParticipant
from app.corporate_access_resources.ca_open_meeting_invitees.models \
    import CAOpenMeetingInvitee
from app.resources.notifications import constants as NOTIFY
from app.resources.cities.models import City
from app.corporate_access_resources.ref_event_types.models import \
    CARefEventType
from app.corporate_access_resources.ref_event_sub_types.models import \
    CARefEventSubType
from app.resources.user_profiles.models import UserProfile
from app.resources.accounts import constants as ACCOUNT
from app.resources.accounts.models import Account
from app.corporate_access_resources.corporate_access_events.models import \
    CorporateAccessEvent
from app.corporate_access_resources.corporate_access_event_invitees.models \
    import CorporateAccessEventInvitee
from app.corporate_access_resources.corporate_access_event_participants.\
    models import CorporateAccessEventParticipant
from app.corporate_access_resources.corporate_access_event_slots.models \
    import CorporateAccessEventSlot
from app.corporate_access_resources.corporate_access_event_agendas.models \
    import CorporateAccessEventAgenda
from app.corporate_access_resources.corporate_access_event_inquiries.models \
    import CorporateAccessEventInquiry, CorporateAccessEventInquiryHistory
from app.corporate_access_resources.corporate_access_event_inquiries import \
    constants as CAEINQ
from app.corporate_access_resources.corporate_access_event_invitees import \
    constants as COINVT
from app.corporate_access_resources.corporate_access_event_stats.models \
    import CorporateAccessEventStats
from app.corporate_access_resources.ca_open_meeting_inquiries.models \
    import CAOpenMeetingInquiryHistory, CAOpenMeetingInquiry
from app.resources.contacts.models import Contact
from app.resources.users.models import User
from app.resources.designations import constants as DESIG

from queueapp.corporate_accesses.stats_tasks import \
    update_corporate_event_stats

from queueapp.ca_open_meetings.notification_tasks import \
    add_caom_cancelled_notification


class CAOpenMeetingAPI(AuthResource):
    """
    CRUD API for managing ca open meeting
    """

    @swag_from('swagger_docs/ca_open_meeting_post.yml')
    def post(self):
        """
        Create a ca open meeting
        """
        ca_open_meeting_schema = CAOpenMeetingSchema()
        # get the form data from the request
        json_data = request.form.to_dict()
        invitee_ids = []
        if 'ca_open_meeting_participants' in json_data:
            json_data['ca_open_meeting_participants'] = json.loads(
                request.form['ca_open_meeting_participants'])
        if 'invitee_ids' in json_data:
            json_data['invitee_ids'] = request.form.getlist('invitee_ids')
        if 'slots' in json_data:
            json_data['slots'] = json.loads(request.form['slots'])
        if 'external_participants' in json_data:
            json_data['external_participants'] = json.loads(
                request.form['external_participants'])
        if 'account_type_preference' in json_data:
            json_data['account_type_preference'] = request.form.getlist(
                'account_type_preference')
        if 'designation_preference' in json_data:
            json_data['designation_preference'] = request.form.getlist(
                'designation_preference')
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            # remove all files when come as string
            json_data, unused = remove_unused_data(json_data=json_data)
            data, errors = ca_open_meeting_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.account_id = g.current_user['account_id']
            data.updated_by = data.created_by
            # participant of system user
            if data.ca_open_meeting_participants:
                for part in data.ca_open_meeting_participants:
                    part.created_by = g.current_user['row_id']
                    part.updated_by = part.created_by
                    part.account_id = g.current_user['account_id']
            if data.slots:
                for slt in data.slots:
                    slt.account_id = g.current_user['account_id']
                    slt.created_by = g.current_user['row_id']
                    slt.updated_by = g.current_user['row_id']
            if data.external_participants:
                for ext_participant in data.external_participants:
                    ext_participant.created_by = g.current_user['row_id']
                    ext_participant.updated_by = ext_participant.created_by
                    ext_participant.account_id = g.current_user['account_id']

            db.session.add(data)
            db.session.commit()
            # manage invitees
            if ca_open_meeting_schema._cached_contact_users:
                for invitee in ca_open_meeting_schema.\
                        _cached_contact_users:
                    if invitee not in data.invitees:
                        db.session.add(CAOpenMeetingInvitee(
                            ca_open_meeting_id=data.row_id,
                            invitee_id=invitee.row_id,
                            created_by=data.created_by,
                            updated_by=data.created_by))
                        invitee_ids.append(invitee.row_id)
                db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (corporate_access_event_id, participant_email)=(
                # 193, tes@gmail.com) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (event_type_id)=(25) is not present
                # in table "corporate_access_ref_event_type".
                # Key (event_sub_type_id)=(25) is not present
                # in table "corporate_access_ref_event_sub_type".
                column = e.orig.diag.message_detail.split('(')[1].split(')')[0]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        attachment = {'files': {}}
        sub_folder = data.file_subfolder_name()
        attachment_full_folder = data.full_folder_path(
            CAOpenMeeting.root_attachment_folder)
        # #TODO: audio video used in future

        if 'attachment' in request.files:
            attachment_path, attachment_name, ferrors = store_file(
                caopenmeetingattachmentfile,
                request.files['attachment'],
                sub_folder=sub_folder, full_folder=attachment_full_folder)
            if ferrors:
                db.session.delete(data)
                db.session.commit()
                return ferrors['message'], ferrors['code']
            attachment['files'][attachment_name] = attachment_path

        try:
            # files upload
            if attachment and attachment['files']:
                # populate db data from file_data
                # parse new files
                if attachment['files']:
                    data.attachment = [
                        fname for fname in attachment['files']][0]
            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            db.session.delete(data)
            db.session.commit()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'CA Open Meeting added: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201

    @swag_from('swagger_docs/ca_open_meeting_delete.yml')
    def delete(self, row_id):
        """
        Delete a ca open meeting
        """
        model = None
        try:
            # first find model
            model = CAOpenMeeting.query.get(row_id)
            if model is None:
                c_abort(404, message='CA Open Meeting '
                        'id: %s does not exist' % str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            db.session.delete(model)
            db.session.commit()
        except Forbidden as e:
            raise e
        except IntegrityError as e:
            if ('is still referenced from table' in
                    e.orig.diag.message_detail.lower()):
                # format of the message:
                # Key (corporate_access_event_id, participant_email)=(
                # 193, tes@gmail.com) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                table = e.orig.diag.message_detail.split('"')[1]
                c_abort(422, message=str(row_id) + ' ' +
                        APP.MSG_REF_OTHER_TABLE + ' ' + table, errors={
                    column: [str(row_id) + ' ' + APP.MSG_REF_OTHER_TABLE +
                             ' ' + table]})
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204

    @swag_from('swagger_docs/ca_open_meeting_get.yml')
    def get(self, row_id):
        """
        Get a ca open meeting by id
        """
        model = None
        try:
            # first find model
            model = CAOpenMeeting.query.filter(
                CAOpenMeeting.row_id == row_id).join(
                CAOpenMeetingInvitee, and_(
                    CAOpenMeeting.row_id ==
                    CAOpenMeetingInvitee.ca_open_meeting_id,
                    CAOpenMeetingInvitee.invitee_id ==
                    g.current_user['row_id']), isouter=True).options(
                contains_eager(CAOpenMeeting.invited)).first()

            if model is None:
                c_abort(404, message='CA Open Meeting id:'
                        ' %s does not exist' % str(row_id))

            invitee_user_ids = [evnt.invitee_id for evnt in
                                model.ca_open_meeting_invitees]
            participant_ids = [evnt.participant_id for evnt in
                               model.ca_open_meeting_participants]
            participant_emails = [evnt.participant_email for evnt in
                                  model.ca_open_meeting_participants]

            # flag for checking open_meeting preferences for account_type
            # and designation, initially set to no match(true)
            not_matching_account_type_and_designation = True
            # if user does not have the designation assigned then the lowest
            # user designation will be considered as user designation
            user_designation = DESIG.DES_LEVEL_OTH
            # check if meeting is open_to_all then, check for current_user
            # account_type and designation in setting preferences
            if model.open_to_all:
                if g.current_user['profile']['designation_link']:
                    user_designation = (g.current_user['profile']
                                        ['designation_link']
                                        ['designation_level'])
                if (user_designation in model.designation_preference and
                        g.current_user['account_type'] in
                        model.account_type_preference):
                    not_matching_account_type_and_designation = False

            # if model is there, if current user is not event creator and
            # not collaborator and not host and not participant and not rsvp
            # and not matches the meeting preferences then
            # current user can not book particular event, so 403 error arise
            if (model.created_by != g.current_user['row_id'] and
                    g.current_user['row_id'] not in participant_ids and
                    g.current_user['email'] not in participant_emails and
                    g.current_user['row_id'] not in invitee_user_ids and
                    (not model.open_to_all or
                        not_matching_account_type_and_designation)):
                c_abort(403)
            result = CAOpenMeetingSchema().dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class CAOpenMeetingListAPI(AuthResource):
    """
    Read API for ca open meeting lists, i.e, more than 1 meeting
    """
    model_class = CAOpenMeeting

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = [
            'attachment_url', 'slots', 'city', 'event_type', 'event_sub_type']
        super(CAOpenMeetingListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)
        main_filter = None
        innerjoin = False
        # build specific extra queries filters
        if extra_query:
            mapper = inspect(self.model_class)
            for f in extra_query:
                # dates
                if f in ['started_at_from', 'started_at_to',
                         'ended_at_from', 'ended_at_to'] and extra_query[f]:
                    # get actual field name
                    fld = f.replace('_from', '').replace('_to', '')
                    # build date query
                    if '_from' in f:
                        query_filters['filters'].append(
                            mapper.columns[fld] >= filters[f])
                        continue
                    if '_to' in f:
                        query_filters['filters'].append(
                            mapper.columns[fld] <= filters[f])
                        continue
                elif f == 'main_filter':
                    main_filter = extra_query[f]
            if 'full_name' in extra_query and extra_query['full_name']:
                full_name = '%' + (extra_query["full_name"]).lower() + '%'
                query_filters['filters'].append(func.concat(
                    func.lower(UserProfile.first_name), ' ',
                    func.lower(UserProfile.last_name)).like(full_name))
            if 'city_name' in extra_query and extra_query['city_name']:
                query_filters['filters'].append(func.lower(
                    City.city_name).like('%' + extra_query[
                        'city_name'].lower() + '%'))
            if 'event_type_name' in extra_query and extra_query[
                    'event_type_name']:
                query_filters['filters'].append(func.lower(
                    CARefEventType.name).like('%' + extra_query[
                        'event_type_name'].lower() + '%'))
            if 'event_sub_type_name' in extra_query and extra_query[
                    'event_sub_type_name']:
                query_filters['filters'].append(func.lower(
                    CARefEventSubType.name).like('%' + extra_query[
                        'event_sub_type_name'].lower() + '%'))
            if 'account_type' in extra_query and extra_query['account_type']:
                query_filters['filters'].append(func.lower(
                    Account.account_type).like('%' + extra_query[
                        'account_type'].lower() + '%'))

        # for union query without current_user filter
        query_filters_union = {}
        query_filters_union['base'] = query_filters['base'][:]
        query_filters_union['filters'] = query_filters['filters'][:]
        query_for_union = self._build_final_query(
            query_filters_union, query_session, operator)

        # check user_designation_level, if exists the assign it to
        # user_designation else, the lowest designation will be considered
        user_designation = DESIG.DES_LEVEL_OTH
        if g.current_user['profile']['designation_link']:
            user_designation = (g.current_user['profile']
                                ['designation_link']['designation_level'])

        # for normal query
        # filter for open to all, and if open_to_all then user account_type
        # matching account_type_preferences and user designation matching
        # designation_preferences will be fetched (satisfying both conditions)
        # cancelled open meeting only fetch for meeting creator and invitee who
        # inquired slot and confirmed
        query_filters['base'].append(or_(
            CAOpenMeeting.created_by == g.current_user['row_id'],
            and_(g.current_user['account_type'] ==
                 any_(CAOpenMeeting.account_type_preference),
                 user_designation ==
                 any_(CAOpenMeeting.designation_preference),
                 CAOpenMeeting.cancelled.is_(False),
                 CAOpenMeeting.open_to_all.is_(True))))

        query = self._build_final_query(query_filters, query_session, operator)

        join_load = [
            # let it know that this is already loaded
            contains_eager(CAOpenMeeting.invited),
            # event type related stuff
            joinedload(CAOpenMeeting.event_type),
            # event sub type related stuff
            joinedload(CAOpenMeeting.event_sub_type),
            # invitees and related stuff
            joinedload(CAOpenMeeting.invitees, innerjoin=innerjoin),
            # participants and related stuff
            joinedload(CAOpenMeeting.participants, innerjoin=innerjoin)]

        # eager load
        query = query.join(
            Account, Account.row_id == CAOpenMeeting.account_id).join(
            UserProfile, UserProfile.user_id == CAOpenMeeting.created_by).join(
            CARefEventType, CARefEventType.row_id ==
            CAOpenMeeting.event_type_id, isouter=True).join(
            CARefEventSubType, CARefEventSubType.row_id ==
            CAOpenMeeting.event_sub_type_id, isouter=True).join(
            City, City.row_id == CAOpenMeeting.city_id, isouter=True).options(
            *join_load)

        query_for_union = query_for_union.join(
            Account, Account.row_id == CAOpenMeeting.account_id).join(
            UserProfile, UserProfile.user_id == CAOpenMeeting.created_by).join(
            CARefEventType, CARefEventType.row_id ==
            CAOpenMeeting.event_type_id, isouter=True).join(
            CARefEventSubType, CARefEventSubType.row_id ==
            CAOpenMeeting.event_sub_type_id, isouter=True).join(
            City, City.row_id == CAOpenMeeting.city_id, isouter=True)

        if not main_filter or main_filter == CAEVENT.MNFT_ALL:
            # for showing events current user either created or invited to
            if g.current_user['account_type'] == ACCOUNT.ACCT_GUEST:
                # if guest user book events by verification token,
                # it's means user_id updated, then guest user can show event
                participant_query = query_for_union.join(
                    CAOpenMeetingParticipant, and_(
                        CAOpenMeetingParticipant.ca_open_meeting_id ==
                        CAOpenMeeting.row_id,
                        CAOpenMeetingParticipant.participant_email ==
                        g.current_user['email'],
                        CAOpenMeeting.cancelled.is_(False))).options(
                    *join_load)
                final_query = participant_query
            else:
                invitee_union = query_for_union.join(
                    CAOpenMeetingInvitee, and_(
                        CAOpenMeetingInvitee.ca_open_meeting_id ==
                        CAOpenMeeting.row_id,
                        CAOpenMeetingInvitee.invitee_id ==
                        g.current_user['row_id'],
                        CAOpenMeeting.cancelled.is_(False))).options(
                    *join_load)
                participant_union = query_for_union.join(
                    CAOpenMeetingParticipant, and_(
                        CAOpenMeetingParticipant.ca_open_meeting_id ==
                        CAOpenMeeting.row_id,
                        CAOpenMeetingParticipant.participant_id ==
                        g.current_user['row_id'],
                        CAOpenMeeting.cancelled.is_(False))).options(
                    *join_load)
                inquiry_confirmed_query = query_for_union.join(
                    CAOpenMeetingInquiry, and_(
                        CAOpenMeetingInquiry.ca_open_meeting_id ==
                        CAOpenMeeting.row_id, CAOpenMeetingInquiry.status ==
                        CAEINQ.CONFIRMED, CAOpenMeetingInquiry.created_by ==
                        g.current_user['row_id'],
                        CAOpenMeeting.cancelled.is_(True))).options(*join_load)
                final_query = query.union(invitee_union).union(
                    participant_union).union(inquiry_confirmed_query)
            # join for contains eager
            final_query = final_query.join(
                CAOpenMeetingInvitee,
                and_(
                    CAOpenMeetingInvitee.ca_open_meeting_id ==
                    CAOpenMeeting.row_id,
                    CAOpenMeetingInvitee.invitee_id ==
                    g.current_user['row_id']), isouter=True)
        elif main_filter == CAEVENT.MNFT_INVITED:
            # for showing events current user is participated for other account
            # for showing meeting current user is invited to
            # for showing open to all meeting if the user account type
            # is in open meeting account_preferences and user designation is
            # in open_meeting designation_preferences
            query_filters['base'].append(and_(
                g.current_user['account_type'] ==
                any_(CAOpenMeeting.account_type_preference),
                user_designation ==
                any_(CAOpenMeeting.designation_preference),
                CAOpenMeeting.cancelled.is_(False),
                CAOpenMeeting.created_by != g.current_user['row_id'],
                CAOpenMeeting.open_to_all.is_(True)))
            query = self._build_final_query(
                query_filters, query_session, operator)
            query = query.join(
                Account,
                Account.row_id == CAOpenMeeting.account_id).join(
                UserProfile, UserProfile.user_id == CAOpenMeeting.created_by
            ).join(
                CARefEventType, CARefEventType.row_id ==
                CAOpenMeeting.event_type_id, isouter=True).join(
                CARefEventSubType, CARefEventSubType.row_id ==
                CAOpenMeeting.event_sub_type_id, isouter=True).join(
                City, City.row_id == CAOpenMeeting.city_id, isouter=True
            ).options(*join_load)

            invited_query = query_for_union.join(
                CAOpenMeetingInvitee, and_(
                    CAOpenMeetingInvitee.ca_open_meeting_id ==
                    CAOpenMeeting.row_id, CAOpenMeetingInvitee.invitee_id ==
                    g.current_user['row_id'],
                    CAOpenMeeting.cancelled.is_(False))).options(*join_load)

            inquiry_confirmed_query = query_for_union.join(
                CAOpenMeetingInquiry, and_(
                    CAOpenMeetingInquiry.ca_open_meeting_id ==
                    CAOpenMeeting.row_id, CAOpenMeetingInquiry.status ==
                    CAEINQ.CONFIRMED, CAOpenMeetingInquiry.created_by ==
                    g.current_user['row_id'])).filter(
                CAOpenMeeting.cancelled.is_(True)).options(*join_load)
            # for participate user
            if g.current_user['account_type'] == ACCOUNT.ACCT_GUEST:
                query_participated = query_for_union.join(
                    CAOpenMeetingParticipant, and_(
                        CAOpenMeetingParticipant.ca_open_meeting_id ==
                        CAOpenMeeting.row_id,
                        CAOpenMeeting.cancelled.is_(False),
                        CAOpenMeetingParticipant.participant_email ==
                        g.current_user['email'])).options(
                    *join_load)
            else:
                query_participated = query_for_union.join(
                    CAOpenMeetingParticipant, and_(
                        CAOpenMeetingParticipant.ca_open_meeting_id ==
                        CAOpenMeeting.row_id,
                        CAOpenMeeting.cancelled.is_(False),
                        CAOpenMeetingParticipant.participant_id ==
                        g.current_user['row_id'],
                        CAOpenMeeting.account_id !=
                        g.current_user['account_id'])).options(
                    *join_load)

            final_query = query.union(invited_query).union(
                inquiry_confirmed_query).union(query_participated)

            final_query = final_query.join(
                CAOpenMeetingInvitee, and_(
                    CAOpenMeetingInvitee.ca_open_meeting_id ==
                    CAOpenMeeting.row_id,
                    CAOpenMeetingInvitee.invitee_id ==
                    g.current_user['row_id']), isouter=True)
        elif main_filter == CAEVENT.MNFT_MINE:
            # for showing only events created by current user
            # and also showing events created by same account user
            query_filters['base'] = []
            query_filters['base'].append(
                CAOpenMeeting.created_by == g.current_user['row_id'])
            query = self._build_final_query(
                query_filters, query_session, operator)
            query = query.join(
                Account,
                Account.row_id == CAOpenMeeting.account_id).join(
                UserProfile, UserProfile.user_id == CAOpenMeeting.created_by
            ).join(
                CARefEventType, CARefEventType.row_id ==
                CAOpenMeeting.event_type_id,
                isouter=True).join(
                CARefEventSubType, CARefEventSubType.row_id ==
                CAOpenMeeting.event_sub_type_id,
                isouter=True).join(
                City, City.row_id == CAOpenMeeting.city_id, isouter=True)
            query = query.options(*join_load)
            # for own company events and current_user participated
            query_participated = query_for_union.join(
                CAOpenMeetingParticipant, and_(
                    CAOpenMeetingParticipant.ca_open_meeting_id ==
                    CAOpenMeeting.row_id,
                    CAOpenMeeting.cancelled.is_(False),
                    CAOpenMeetingParticipant.participant_id ==
                    g.current_user['row_id'], CAOpenMeeting.account_id ==
                    g.current_user['account_id'])).options(
                *join_load)

            final_query = query.union(query_participated)
            # join for event invited
            final_query = final_query.join(
                CAOpenMeetingInvitee,
                and_(
                    CAOpenMeetingInvitee.ca_open_meeting_id ==
                    CAOpenMeeting.row_id,
                    CAOpenMeetingInvitee.invitee_id ==
                    g.current_user['row_id']), isouter=True)
        if sort:
            for col in sort['sort_by']:
                if col == 'event_type_name':
                    col = 'name'
                    mapper = inspect(CARefEventSubType)
                    final_query = final_query.join(
                        CARefEventSubType,
                        CAOpenMeeting.event_sub_type_id ==
                        CARefEventSubType.row_id)
                elif col == 'company_name':
                    col = 'account_name'
                    mapper = inspect(Account)
                    final_query = final_query.join(
                        Account,
                        Account.row_id == CAOpenMeeting.account_id)
                elif col == 'city':
                    col = 'city_name'
                    mapper = inspect(City)
                    final_query = final_query.join(
                        City, City.row_id == CAOpenMeeting.city_id,
                        isouter=True)
                else:
                    continue
                sort_fxn = 'asc'
                if sort['sort'] == 'dsc':
                    sort_fxn = 'desc'
                order.append(getattr(mapper.columns[col], sort_fxn)())

        return final_query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/ca_open_meeting_get_list.yml')
    def get(self):
        """
        Get the list
        """
        ca_open_meeting_read_schema = CAOpenMeetingReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            ca_open_meeting_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(
                    filters, pfields, sort, pagination, db.session.query(
                        CAOpenMeeting), operator)
            # making a copy of the main output schema
            ca_open_meeting_schema = CAOpenMeetingSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                ca_open_meeting_schema = CAOpenMeetingSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching ca open meetings found')
            result = ca_open_meeting_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            abort(500)
        return {'results': result.data, 'total': total}, 200


class CAOpenMeetingCancelledAPI(AuthResource):
    """
    API for maintaining ca open meeting cancelled feature
    """

    @swag_from('swagger_docs/ca_open_meeting_cancel_put.yml')
    def put(self, row_id):
        """
        Update a ca open meeting cancelled value
        """
        # first find model
        model = None
        try:
            model = CAOpenMeeting.query.get(row_id)
            if model is None:
                c_abort(404, message='CA Open Meeting id: %s'
                        'does not exist' % str(row_id))
            # caom to be used for notifications
            caom_id = model.row_id
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            if not model.cancelled:
                model.cancelled = True
                db.session.add(model)
                db.session.commit()
                # send notifications to slot inquiry confirmed users
                add_caom_cancelled_notification.s(
                    True, caom_id, NOTIFY.NT_CAOM_CANCELLED).delay()
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Cancelled CA Open Meeting id: %s' %
                str(row_id)}, 200


class CAOpenMeetingToCAEventConversionAPI(AuthResource):
    """
    When open meeting creator want to convert open meeting to CAEvent
    """

    def post(self, row_id):
        """
        add data ca open meeting to CAEvent
        :param row_id: row_id of ca open meeting
        """

        ca_open_meeting_data = None
        try:
            # first find model
            ca_open_meeting_data = CAOpenMeeting.query.get(row_id)
            if ca_open_meeting_data is None:
                c_abort(404, message='CA Open Meeting '
                                     'id: %s does not exist' % str(row_id))
            # check ownership
            if ca_open_meeting_data.created_by != g.current_user['row_id']:
                abort(403)

            if ca_open_meeting_data.is_draft:
                c_abort(422, message="In draft mode, can't be converted to"
                        " CAEvent")

            if ca_open_meeting_data.is_converted:
                c_abort(422, message="It's already converted, can't be "
                        "converted to CAEvent")

            attrs = ['account_id', 'created_by', 'updated_by', 'event_type_id',
                     'event_sub_type_id', 'title', 'description', 'started_at',
                     'ended_at', 'city_id', 'state_id', 'country_id',
                     'dial_in_detail', 'alternative_dial_in_detail',
                     'is_draft', 'cancelled', 'attachment', 'open_to_all',
                     'account_type_preference']
            open_meet_args = {'is_open_meeting': True}
            for attr in attrs:
                open_meet_args[attr] = getattr(ca_open_meeting_data, attr)
            # insert data into CAEvent
            caevent = CorporateAccessEvent(**open_meet_args)
            db.session.add(caevent)
            db.session.commit()
            # insert caevent stats
            caevent_stats = CorporateAccessEventStats(
                corporate_access_event_id=caevent.row_id)
            db.session.add(caevent_stats)
            # insert data CAEvent participant
            if ca_open_meeting_data.ca_open_meeting_participants:
                participant_attrs = [
                    'created_by', 'updated_by', 'participant_id',
                    'participant_email', 'participant_first_name',
                    'participant_last_name', 'participant_designation',
                    'sequence_id']
                part_args = {'corporate_access_event_id': caevent.row_id}
                for caopen_part in ca_open_meeting_data. \
                        ca_open_meeting_participants:
                    for attr in participant_attrs:
                        part_args[attr] = getattr(caopen_part, attr)
                    caevent_participant = CorporateAccessEventParticipant(
                        **part_args)
                    db.session.add(caevent_participant)
            # insert data into CAEvent slot
            invitee_ids = []
            slot_inquirer = []
            if ca_open_meeting_data.slots:
                if ca_open_meeting_data.event_sub_type.has_slots:
                    # for get all inquirer for all slots
                    for slt in ca_open_meeting_data.slots:
                        inquirer = [inq.creator for inq in
                                    slt.ca_open_meeting_inquiries]
                        slot_inquirer.extend(inquirer)
                        slot_inquirer = list(set(slot_inquirer))
                    for caopen_slt in ca_open_meeting_data.slots:
                        caevntslot = CorporateAccessEventSlot(
                            account_id=caopen_slt.account_id,
                            created_by=caopen_slt.created_by,
                            updated_by=caopen_slt.updated_by,
                            event_id=caevent.row_id,
                            slot_type=caopen_slt.slot_type,
                            slot_name=caopen_slt.slot_name,
                            description=caopen_slt.description,
                            started_at=caopen_slt.started_at,
                            ended_at=caopen_slt.ended_at,
                            bookable_seats=caopen_slt.bookable_seats,
                            booked_seats=caopen_slt.booked_seats,
                            address=caopen_slt.address,
                            text_1=caopen_slt.text_1,
                            text_2=caopen_slt.text_2)
                        db.session.add(caevntslot)
                        db.session.commit()
                        # insert into inquiry data if inquiry confirmed by
                        # creator
                        # copy all inquirer
                        slot_disallowed = slot_inquirer[:]
                        for caopeninq in caopen_slt.ca_open_meeting_inquiries:
                            if caopeninq.status == CAEINQ.CONFIRMED:
                                if caopeninq.creator in slot_disallowed:
                                    # if confirm inquirer user so remove
                                    # from slot inquirer
                                    slot_disallowed.remove(caopeninq.creator)
                                # list for invitee data
                                invitee_ids.append(caopeninq.created_by)
                                # insert inquiry data
                                caevnt_inq = CorporateAccessEventInquiry(
                                    created_by=caopeninq.created_by,
                                    updated_by=caopeninq.updated_by,
                                    corporate_access_event_id=caevent.row_id,
                                    corporate_access_event_slot_id=caevntslot.
                                    row_id, status=caopeninq.status)
                                db.session.add(caevnt_inq)
                        # final disallow inquirer for particular slot
                        caevntslot.disallowed = slot_disallowed[:]
                        for caopenhistory in \
                                CAOpenMeetingInquiryHistory.query.\
                                filter(CAOpenMeetingInquiryHistory.
                                       ca_open_meeting_slot_id == caopen_slt.
                                       row_id).all():
                            # inquiry history data only which is confirmed
                            caevent_inq_his = \
                                CorporateAccessEventInquiryHistory(
                                    created_by=caopenhistory.created_by,
                                    updated_by=caopenhistory.updated_by,
                                    corporate_access_event_id=caevent.row_id,
                                    corporate_access_event_slot_id=caevntslot.
                                    row_id, status=caopenhistory.status)
                            db.session.add(caevent_inq_his)
                else:
                    # insert data into agenda if sub type is not has_slots
                    for caopen_slt in ca_open_meeting_data.slots:
                        caeventagenda = CorporateAccessEventAgenda(
                            created_by=caopen_slt.created_by,
                            updated_by=caopen_slt.updated_by,
                            corporate_access_event_id=caevent.row_id,
                            title=dt.strftime(
                                caopen_slt.started_at, '%d/%m/%Y'),
                            started_at=caopen_slt.started_at,
                            ended_at=caopen_slt.ended_at,
                            description=caopen_slt.description,
                            address=caopen_slt.address)
                        db.session.add(caeventagenda)
                        # append invitee list when not has_slots event sub type
                        for caopeninq in caopen_slt.ca_open_meeting_inquiries:
                            if caopeninq.status == CAEINQ.CONFIRMED:
                                invitee_ids.append(caopeninq.created_by)
            # invitee insert
            if invitee_ids:
                invitee_data = User.query.filter(User.row_id.in_(
                    invitee_ids)).all()
                for invt in invitee_data:
                    contact_data = Contact.query.filter(or_(
                        and_(Contact.sent_by == invt.row_id,
                             Contact.sent_to == g.current_user['row_id']),
                        and_(Contact.sent_to == invt.row_id,
                             Contact.sent_by == g.current_user['row_id']))
                    ).first()
                    # if invitee in contact list of current user, its insert as
                    # a normal invitee
                    if contact_data:
                        caevnt_invitee = CorporateAccessEventInvitee(
                            created_by=caevent.created_by,
                            updated_by=caevent.created_by,
                            corporate_access_event_id=caevent.row_id,
                            invitee_id=invt.row_id,
                            user_id=invt.row_id)
                        if not ca_open_meeting_data.event_sub_type.has_slots:
                            caevnt_invitee.status = COINVT.JOINED
                        db.session.add(caevnt_invitee)
                    else:
                        # if invitee not in contact list of current user,
                        # its insert as a external invitee
                        caevnt_invitee = CorporateAccessEventInvitee(
                            created_by=caevent.created_by,
                            updated_by=caevent.created_by,
                            corporate_access_event_id=caevent.row_id,
                            invitee_email=invt.email,
                            invitee_first_name=invt.profile.first_name,
                            invitee_last_name=invt.profile.last_name,
                            invitee_designation=invt.profile.designation,
                            user_id=invt.row_id)
                        if not ca_open_meeting_data.event_sub_type.has_slots:
                            caevnt_invitee.status = COINVT.JOINED
                        db.session.add(caevnt_invitee)

            # copy open meeting attachment file to caevent attachment in local
            # as well as in s3
            if ca_open_meeting_data.attachment:
                db.session.commit()
                attachment_full_folder = ca_open_meeting_data.full_folder_path(
                    CAOpenMeeting.root_attachment_folder)
                dest_path = caevent.full_folder_path(
                    CorporateAccessEvent.root_attachment_folder)
                f_name = ca_open_meeting_data.attachment
                sub_folder = caevent.file_subfolder_name()
                # #TODO: copy file not working!!!
                # copy_file(attachment_full_folder, dest_path, sub_folder,
                #          f_name)
            db.session.commit()
            # after converted into ca event update is_converted update into
            # true from open meeting
            ca_open_meeting_data.is_converted = True
            db.session.add(ca_open_meeting_data)
            db.session.commit()
            update_corporate_event_stats.s(True, caevent.row_id).delay()
        except Forbidden as e:
            db.session.delete(caevent)
            db.session.commit()
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.delete(caevent)
            db.session.commit()
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Corporate Access Event added: %s' %
                           str(caevent.row_id), 'row_id': caevent.row_id}, 201
