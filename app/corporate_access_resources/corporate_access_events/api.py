"""
API endpoints for "corporate access event" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g, json
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from webargs.flaskparser import parser
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import load_only, joinedload, contains_eager
from sqlalchemy import and_, or_, any_, func
from flasgger.utils import swag_from

from app import (
    db, c_abort, caeventinvitelogofile, caeventinvitebannerfile,
    caeventattachmentfile, caeventtranscriptfile, caeventaudiofile, flaskapp)
from app.base.api import AuthResource, BaseResource
from app.base import constants as APP
from app.base.schemas import BaseCommonSchema
from app.corporate_access_resources.corporate_access_events import \
    constants as CAEVENT
from app.common.helpers import store_file, delete_files, \
    verify_event_book_token
from app.corporate_access_resources.corporate_access_events.models \
    import CorporateAccessEvent
from app.corporate_access_resources.corporate_access_events.schemas import (
    CorporateAccessEventSchema, CorporateAccessEventReadArgsSchema,
    CorporateAccessEventEditSchema, CorporateAccessNoAuthSchema)
from app.corporate_access_resources.corporate_access_events.helpers import (
    remove_unused_data, remove_participant_or_rsvp_sequence_id,
    check_external_invitee_exists_in_user)
from app.corporate_access_resources.corporate_access_event_participants.\
    models import CorporateAccessEventParticipant
from app.corporate_access_resources.corporate_access_event_hosts.models \
    import CorporateAccessEventHost
from app.corporate_access_resources.corporate_access_event_invitees.models \
    import CorporateAccessEventInvitee
from app.corporate_access_resources.corporate_access_event_slots.schemas \
    import CorporateAccessEventSlotSchema
from app.corporate_access_resources.corporate_access_event_rsvps.schemas \
    import CorporateAccessEventRSVPSchema
from app.corporate_access_resources.corporate_access_event_collaborators.\
    schemas import CorporateAccessEventCollaboratorSchema
from app.corporate_access_resources.corporate_access_event_collaborators.\
    models import CorporateAccessEventCollaborator
from app.corporate_access_resources.corporate_access_event_rsvps.models \
    import CorporateAccessEventRSVP
from app.corporate_access_resources.corporate_access_event_invitees.schemas \
    import CorporateAccessEventInviteeSchema
from app.corporate_access_resources.corporate_access_event_hosts.schemas \
    import CorporateAccessEventHostSchema
from app.corporate_access_resources.corporate_access_event_participants.\
    schemas import CorporateAccessEventParticipantSchema
from app.resources.accounts import constants as ACCOUNT
from app.corporate_access_resources.corporate_access_event_stats.\
    models import CorporateAccessEventStats
from app.corporate_access_resources.corporate_access_event_slots.models \
    import CorporateAccessEventSlot
from app.corporate_access_resources.corporate_access_event_agendas.models \
    import CorporateAccessEventAgenda
from app.corporate_access_resources.corporate_access_event_agendas.schemas \
    import CorporateAccessEventAgendaSchema
from app.corporate_access_resources.ref_event_types.models import \
    CARefEventType
from app.resources.users.models import User
from app.resources.accounts.models import Account
from app.resources.notifications import constants as NOTIFY
from app.global_search.helpers import (
    add_to_index, remove_from_index
)
from app.corporate_access_resources.ref_event_sub_types.models import (
    CARefEventSubType)
from app.resources.cities.models import City
from app.resources.users.helpers import include_current_users_groups_only

from queueapp.corporate_accesses.stats_tasks import (
    update_corporate_event_stats)
from queueapp.corporate_accesses.email_tasks import (
    send_corporate_access_event_launch_email,
    send_corporate_access_event_new_invitee_email,
    send_corporate_access_event_updated_email,
    send_corporate_access_event_invitee_updated_email,
    send_corporate_access_event_cancellation_email)
from queueapp.corporate_accesses.notification_tasks import (
    add_cae_invite_added_notification,
    add_cae_host_added_notification,
    add_cae_rsvp_added_notification,
    add_cae_participant_added_notification,
    add_cae_collaborator_added_notification,
    add_cae_updated_invitee_notification,
    add_cae_updated_host_notification,
    add_cae_updated_participant_notification,
    add_cae_updated_rsvp_notification,
    add_cae_updated_collaborator_notification,
    add_cae_cancelled_invitee_notification)


class CorporateAccessEventAPI(AuthResource):
    """
    CRUD API for managing Corporate Access Event
    """

    @swag_from('swagger_docs/corporate_access_events_post.yml')
    def post(self):
        """
        Create a Corporate Access Event
        """
        corporate_access_event_schema = CorporateAccessEventSchema()
        # get the form data from the request
        input_data = None
        input_data = parser.parse(
            BaseCommonSchema(), locations=('querystring',))
        json_data = request.form.to_dict()
        invitee_ids = []
        host_ids = []
        if 'corporate_access_event_participants' in json_data:
            json_data['corporate_access_event_participants'] = json.loads(
                request.form['corporate_access_event_participants'])
        if 'host_ids' in json_data:
            json_data['host_ids'] = request.form.getlist('host_ids')
        if 'invitee_ids' in json_data:
            json_data['invitee_ids'] = request.form.getlist('invitee_ids')
        if 'file_ids' in json_data:
            json_data['file_ids'] = request.form.getlist('file_ids')
        if 'participant_company_ids' in json_data:
            json_data['participant_company_ids'] = request.form.getlist(
                'participant_company_ids')
        if 'slots' in json_data:
            json_data['slots'] = json.loads(request.form['slots'])
        if 'rsvps' in json_data:
            json_data['rsvps'] = json.loads(request.form['rsvps'])
        if 'collaborators' in json_data:
            json_data['collaborators'] = json.loads(
                request.form['collaborators'])
        if 'external_invitees' in json_data:
            json_data['external_invitees'] = json.loads(
                request.form['external_invitees'])
        if 'external_hosts' in json_data:
            json_data['external_hosts'] = json.loads(
                request.form['external_hosts'])
        if 'external_participants' in json_data:
            json_data['external_participants'] = json.loads(
                request.form['external_participants'])
        if 'agendas' in json_data:
            json_data['agendas'] = json.loads(request.form['agendas'])
        if 'cc_emails' in json_data:
            json_data['cc_emails'] = request.form.getlist('cc_emails')
        if 'account_type_preference' in json_data:
            json_data['account_type_preference'] = request.form.getlist(
                'account_type_preference')
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            # remove all files when come as string
            json_data, unused = remove_unused_data(json_data=json_data)
            data, errors = corporate_access_event_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            # permission for meeting type events
            if (corporate_access_event_schema._cached_event_type.is_meeting and
                    corporate_access_event_schema._cached_meeting_account):
                # get account_type
                meeting_account_type = corporate_access_event_schema.\
                    _cached_meeting_account.account_type
                # if current user type is corporate, private and sme then
                # they can invite only sell-side, buy-side and general investor
                # vice-versa
                if (g.current_user['account_type'] in [
                        ACCOUNT.ACCT_CORPORATE, ACCOUNT.ACCT_SME,
                        ACCOUNT.ACCT_PRIVATE] and
                        meeting_account_type not in [
                        ACCOUNT.ACCT_SELL_SIDE_ANALYST,
                        ACCOUNT.ACCT_BUY_SIDE_ANALYST,
                        ACCOUNT.ACCT_GENERAL_INVESTOR]):
                    c_abort(403)
                elif (g.current_user['account_type'] in [
                        ACCOUNT.ACCT_SELL_SIDE_ANALYST,
                        ACCOUNT.ACCT_BUY_SIDE_ANALYST,
                        ACCOUNT.ACCT_GENERAL_INVESTOR] and
                        meeting_account_type not in [
                        ACCOUNT.ACCT_CORPORATE, ACCOUNT.ACCT_SME,
                        ACCOUNT.ACCT_PRIVATE]):
                    c_abort(403)

            # general investor can create only meeting type events
            if (g.current_user['account_type'] ==
                    ACCOUNT.ACCT_GENERAL_INVESTOR and
                    not corporate_access_event_schema.\
                    _cached_event_type.is_meeting):
                c_abort(401)

            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.account_id = g.current_user['account_id']
            data.updated_by = data.created_by
            data.stats = CorporateAccessEventStats()
            # participant of system user
            if data.corporate_access_event_participants:
                for part in data.corporate_access_event_participants:
                    part.created_by = g.current_user['row_id']
                    part.updated_by = part.created_by
                    part.account_id = g.current_user['account_id']
            if data.slots:
                for slt in data.slots:
                    slt.account_id = g.current_user['account_id']
                    slt.created_by = g.current_user['row_id']
                    slt.updated_by = g.current_user['row_id']
            if data.rsvps:
                for rsvp in data.rsvps:
                    rsvp.created_by = g.current_user['row_id']
                    rsvp.updated_by = g.current_user['row_id']
            if data.agendas:
                for agenda in data.agendas:
                    agenda.created_by = g.current_user['row_id']
                    agenda.updated_by = g.current_user['row_id']
            if data.collaborators:
                for collaborator in data.collaborators:
                    collaborator.created_by = g.current_user['row_id']
                    collaborator.updated_by = g.current_user['row_id']
            if data.external_invitees:
                for ext_invitee in data.external_invitees:
                    user_row_id = check_external_invitee_exists_in_user(
                        ext_invitee.invitee_email)
                    if user_row_id:
                        ext_invitee.user_id = user_row_id
                    ext_invitee.created_by = g.current_user['row_id']
                    ext_invitee.updated_by = ext_invitee.created_by
                    ext_invitee.account_id = g.current_user['account_id']
            if data.external_hosts:
                for ext_host in data.external_hosts:
                    ext_host.created_by = g.current_user['row_id']
                    ext_host.updated_by = ext_host.created_by
                    ext_host.account_id = g.current_user['account_id']
            if data.external_participants:
                for ext_participant in data.external_participants:
                    ext_participant.created_by = g.current_user['row_id']
                    ext_participant.updated_by = ext_participant.created_by
                    ext_participant.account_id = g.current_user['account_id']

            db.session.add(data)
            db.session.commit()
            # manage files list
            if corporate_access_event_schema._cached_files:
                for cf in corporate_access_event_schema._cached_files:
                    if cf not in data.files:
                        data.files.append(cf)
            db.session.add(data)
            db.session.commit()

            # manage participant companies list
            if corporate_access_event_schema._cached_participant_companies:
                for pc in corporate_access_event_schema. \
                        _cached_participant_companies:
                    if pc not in data.caevent_participant_companies:
                        data.caevent_participant_companies.append(pc)
                db.session.add(data)
                db.session.commit()

            # manage hosts
            if corporate_access_event_schema._cached_host_users:
                host_ids = []
                for host in corporate_access_event_schema._cached_host_users:
                    if host not in data.hosts:
                        db.session.add(CorporateAccessEventHost(
                            corporate_access_event_id=data.row_id,
                            host_id=host.row_id,
                            created_by=data.created_by,
                            updated_by=data.created_by))
                        host_ids.append(host.row_id)
                db.session.commit()
            # manage invitees
            if corporate_access_event_schema._cached_contact_users:
                for invitee in corporate_access_event_schema.\
                        _cached_contact_users:
                    if invitee not in data.invitees:
                        db.session.add(CorporateAccessEventInvitee(
                            corporate_access_event_id=data.row_id,
                            invitee_id=invitee.row_id,
                            # directly assign user_id for system user
                            user_id=invitee.row_id,
                            created_by=data.created_by,
                            updated_by=data.created_by))
                        invitee_ids.append(invitee.row_id)
                db.session.commit()
            update_corporate_event_stats.s(True, data.row_id).delay()
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

        invite_logo = {'files': {}}
        invite_banner = {'files': {}}
        attachment = {'files': {}}
        audio = {'files': {}}
        transcript = {'files': {}}
        sub_folder = data.file_subfolder_name()
        invite_logo_full_folder = data.full_folder_path(
            CorporateAccessEvent.root_invite_logo_folder)
        invite_banner_full_folder = data.full_folder_path(
            CorporateAccessEvent.root_invite_banner_folder)
        attachment_full_folder = data.full_folder_path(
            CorporateAccessEvent.root_attachment_folder)
        audio_full_folder = data.full_folder_path(
            CorporateAccessEvent.root_audio_folder)
        transcript_full_folder = data.full_folder_path(
            CorporateAccessEvent.root_transcript_folder)
        # #TODO: audio video used in future

        if 'invite_logo_filename' in request.files:
            logo_path, logo_name, ferrors = store_file(
                caeventinvitelogofile, request.files['invite_logo_filename'],
                sub_folder=sub_folder, full_folder=invite_logo_full_folder)
            if ferrors:
                db.session.delete(data)
                db.session.commit()
                return ferrors['message'], ferrors['code']
            invite_logo['files'][logo_name] = logo_path
        if 'invite_banner_filename' in request.files:
            banner_path, banner_name, ferrors = store_file(
                caeventinvitebannerfile,
                request.files['invite_banner_filename'],
                sub_folder=sub_folder, full_folder=invite_banner_full_folder)
            if ferrors:
                db.session.delete(data)
                db.session.commit()
                return ferrors['message'], ferrors['code']
            invite_banner['files'][banner_name] = banner_path
        if 'audio_filename' in request.files:
            audio_path, audio_name, ferrors = store_file(
                caeventaudiofile, request.files['audio_filename'],
                sub_folder=sub_folder, full_folder=audio_full_folder)
            if ferrors:
                db.session.delete(data)
                db.session.commit()
                return ferrors['message'], ferrors['code']
            audio['files'][audio_name] = audio_path
        if 'transcript_filename' in request.files:
            transcript_path, transcript_name, ferrors = store_file(
                caeventtranscriptfile, request.files['transcript_filename'],
                sub_folder=sub_folder, full_folder=transcript_full_folder)
            if ferrors:
                db.session.delete(data)
                db.session.commit()
                return ferrors['message'], ferrors['code']
            transcript['files'][transcript_name] = transcript_path
        if 'attachment' in request.files:
            attachment_path, attachment_name, ferrors = store_file(
                caeventattachmentfile,
                request.files['attachment'],
                sub_folder=sub_folder, full_folder=attachment_full_folder)
            if ferrors:
                db.session.delete(data)
                db.session.commit()
                return ferrors['message'], ferrors['code']
            attachment['files'][attachment_name] = attachment_path

        try:
            # files upload
            if invite_logo and invite_logo['files']:
                # populate db data from file_data
                # parse new files
                if invite_logo['files']:
                    data.invite_logo_filename = [
                        fname for fname in invite_logo['files']][0]
            if invite_banner and invite_banner['files']:
                # populate db data from file_data
                # parse new files
                if invite_banner['files']:
                    data.invite_banner_filename = [
                        fname for fname in invite_banner['files']][0]
            if audio and audio['files']:
                # populate db data from file_data
                # parse new files
                if audio['files']:
                    data.audio_filename = [
                        fname for fname in audio['files']][0]
            if transcript and transcript['files']:
                # populate db data from file_data
                # parse new files
                if transcript['files']:
                    data.transcript_filename = [
                        fname for fname in transcript['files']][0]
            if attachment and attachment['files']:
                # populate db data from file_data
                # parse new files
                if attachment['files']:
                    data.attachment = [
                        fname for fname in attachment['files']][0]
            if 'launch' in input_data and input_data['launch']:
                data.is_draft = False
            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()

            # condition for sending emails, if satisfies send emails
            if data.is_draft is False:
                if invitee_ids or data.external_invitees:
                    add_cae_invite_added_notification.s(
                        True, data.row_id,
                        NOTIFY.NT_COR_EVENT_INVITED).delay()
                if host_ids or data.external_hosts:
                    add_cae_host_added_notification.s(
                        True, data.row_id,
                        NOTIFY.NT_COR_HOST_ADDED).delay()
                # #TODO: used in future
                # if data.rsvps:
                #     add_cae_rsvp_added_notification.s(
                #         True, data.row_id, NOTIFY.NT_COR_RSVP_ADDED).delay()

                # participant added
                if (data.corporate_access_event_participants or
                        data.external_participants):
                    add_cae_participant_added_notification.s(
                        True, data.row_id,
                        NOTIFY.NT_COR_PARTICIPANT_ADDED).delay()
                # collaborator added
                if data.collaborators:
                    add_cae_collaborator_added_notification.s(
                        True, data.row_id,
                        NOTIFY.NT_COR_COLLABORATOR_ADDED).delay()
                send_corporate_access_event_launch_email.s(
                    True, data.row_id, not_for_creator=False).delay()
                # true specifies mail sending task is in queue
                data.is_in_process = True
                db.session.add(data)
                db.session.commit()

            if ('USE_ELASTIC_SEARCH' in flaskapp.config
                    and flaskapp.config['USE_ELASTIC_SEARCH']):
                add_to_index(APP.DF_ES_INDEX, data)
        except Exception as e:
            db.session.rollback()
            db.session.delete(data)
            db.session.commit()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Corporate Access Event added: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201

    @swag_from('swagger_docs/corporate_access_events_put.yml')
    def put(self, row_id):
        """
        Update a Corporate Access Event
        """
        corporate_access_event_edit_schema = CorporateAccessEventEditSchema()
        # first find model
        model = None
        collaborator_ids = []
        invitee_ids = []
        host_ids = []
        collaborator_editor = False
        try:
            # get data from query string using parsing
            input_data = None
            input_data = parser.parse(
                BaseCommonSchema(), locations=('querystring',))
            model = CorporateAccessEvent.query.get(row_id)
            if model is None:
                c_abort(404, message='Corporate Access Event id: '
                        '%s does not exist' % str(row_id))
            collaborator_ids = [col.collaborator_id for col in
                                model.collaborators]
            # is_draft status, to be used for sending email for cae launch
            old_is_draft = model.is_draft
            # old_rsvps, for checking if new rsvps are added and
            # send emails for updated rsvps
            rsvp_old_list = []
            for rsvp in model.rsvps:
                rsvp_old_list.append(
                    {rsvp.email: rsvp.contact_person})
            ext_invt_old_list = []  # old external invitee list
            ext_invt_update_list = []  # updated external invitee list
            invitee_list = []  # to check diff between old and update list
            # check ownership
            # for group account type user check with account id for
            # child account
            if ((model.created_by != g.current_user['row_id'] or
                    model.account_id != g.current_user['account_id']) and
                    g.current_user['row_id'] not in collaborator_ids):
                abort(403)
            # for is_meeting validation in schema
            corporate_access_event_edit_schema._event_type = \
                model.event_type
        except HTTPException as e:
            raise e
        except Exception as e:
            abort(500)
        # collaborators can change only slots and rsvp
        if collaborator_ids and g.current_user['row_id'] in collaborator_ids:
            collaborator_editor = True

        invite_logo = {'files': {}}
        invite_banner = {'files': {}}
        audio = {'files': {}}
        transcript = {'files': {}}
        attachment = {'files': {}}
        sub_folder = model.file_subfolder_name()
        invite_logo_full_folder = model.full_folder_path(
            CorporateAccessEvent.root_invite_logo_folder)
        invite_banner_full_folder = model.full_folder_path(
            CorporateAccessEvent.root_invite_banner_folder)
        attachment_full_folder = model.full_folder_path(
            CorporateAccessEvent.root_attachment_folder)
        audio_full_folder = model.full_folder_path(
            CorporateAccessEvent.root_audio_folder)
        transcript_full_folder = model.full_folder_path(
            CorporateAccessEvent.root_transcript_folder)
        if not collaborator_editor:
            if 'invite_logo_filename' in request.files:
                logo_path, logo_name, ferrors = store_file(
                    caeventinvitelogofile,
                    request.files['invite_logo_filename'],
                    sub_folder=sub_folder, full_folder=invite_logo_full_folder)
                if ferrors:
                    return ferrors['message'], ferrors['code']
                invite_logo['files'][logo_name] = logo_path
            if 'invite_banner_filename' in request.files:
                banner_path, banner_name, ferrors = store_file(
                    caeventinvitebannerfile,
                    request.files['invite_banner_filename'],
                    sub_folder=sub_folder,
                    full_folder=invite_banner_full_folder)
                if ferrors:
                    return ferrors['message'], ferrors['code']
                invite_banner['files'][banner_name] = banner_path
            if 'attachment' in request.files:
                attachment_path, attachment_name, ferrors = store_file(
                    caeventattachmentfile,
                    request.files['attachment'],
                    sub_folder=sub_folder, full_folder=attachment_full_folder)
                if ferrors:
                    return ferrors['message'], ferrors['code']
                attachment['files'][attachment_name] = attachment_path
            if 'audio_filename' in request.files:
                audio_path, audio_name, ferrors = store_file(
                    caeventaudiofile, request.files['audio_filename'],
                    sub_folder=sub_folder, full_folder=audio_full_folder)
                if ferrors:
                    return ferrors['message'], ferrors['code']
                audio['files'][audio_name] = audio_path
            if 'transcript_filename' in request.files:
                transcript_path, transcript_name, ferrors = store_file(
                    caeventtranscriptfile,
                    request.files['transcript_filename'],
                    sub_folder=sub_folder, full_folder=transcript_full_folder)
                if ferrors:
                    return ferrors['message'], ferrors['code']
                transcript['files'][transcript_name] = transcript_path

            if 'invite_logo_filename' in request.form:
                invite_logo['delete'] = []
                if (request.form['invite_logo_filename'] ==
                        model.invite_logo_filename):
                    invite_logo['delete'].append(
                        request.form['invite_logo_filename'])
                    if invite_logo['delete']:
                        # delete all mentioned files
                        ferrors = delete_files(
                            invite_logo['delete'], sub_folder=sub_folder,
                            full_folder=invite_logo_full_folder)
                        if ferrors:
                            return ferrors['message'], ferrors['code']
            if 'invite_banner_filename' in request.form:
                invite_banner['delete'] = []
                if (request.form['invite_banner_filename'] ==
                        model.invite_banner_filename):
                    invite_banner['delete'].append(
                        request.form['invite_banner_filename'])
                    if invite_banner['delete']:
                        # delete all mentioned files
                        ferrors = delete_files(
                            invite_banner['delete'], sub_folder=sub_folder,
                            full_folder=invite_banner_full_folder)
                        if ferrors:
                            return ferrors['message'], ferrors['code']
            if 'audio_filename' in request.form:
                audio['delete'] = []
                if (request.form['audio_filename'] ==
                        model.audio_filename):
                    audio['delete'].append(
                        request.form['audio_filename'])
                    if audio['delete']:
                        # delete all mentioned files
                        ferrors = delete_files(
                            audio['delete'], sub_folder=sub_folder,
                            full_folder=audio_full_folder)
                        if ferrors:
                            return ferrors['message'], ferrors['code']
            if 'transcript_filename' in request.form:
                transcript['delete'] = []
                if (request.form['transcript_filename'] ==
                        model.transcript_filename):
                    transcript['delete'].append(
                        request.form['transcript_filename'])
                    if transcript['delete']:
                        # delete all mentioned files
                        ferrors = delete_files(
                            transcript['delete'], sub_folder=sub_folder,
                            full_folder=transcript_full_folder)
                        if ferrors:
                            return ferrors['message'], ferrors['code']
            if 'attachment' in request.form:
                attachment['delete'] = []
                if (request.form['attachment'] ==
                        model.attachment):
                    attachment['delete'].append(
                        request.form['attachment'])
                    if attachment['delete']:
                        # delete all mentioned files
                        ferrors = delete_files(
                            attachment['delete'], sub_folder=sub_folder,
                            full_folder=attachment_full_folder)
                        if ferrors:
                            return ferrors['message'], ferrors['code']

        # get the json data from the request
        json_data = request.form
        if not json_data:
            c_abort(400)
        slot_data = None  # for slot data
        rsvp_data = None  # for rsvp data
        collaborator_data = None  # for collaborator data
        agenda_data = None
        cae_participant_data = None
        external_invitees_data = None  # for external invitees data
        external_host_data = None  # for external host data
        external_participant_data = None  # for external participant data
        try:
            # get the json data from the request
            json_data = request.form.to_dict()
            # event type is meeting so this type event can limited changes
            if model.event_type.is_meeting:
                json_data, unused = remove_unused_data(json_data)
            invitee_ids = []
            c_json_data = {}  # json_data copy for collaborators
            if 'corporate_access_event_participants' in json_data:
                del json_data['corporate_access_event_participants']
                cae_participant_data = json.loads(request.form[
                    'corporate_access_event_participants'])
            if 'host_ids' in json_data:
                json_data['host_ids'] = request.form.getlist('host_ids')
            if 'file_ids' in json_data:
                json_data['file_ids'] = request.form.getlist('file_ids')
            if 'participant_company_ids' in json_data:
                json_data['participant_company_ids'] = request.form.getlist(
                    'participant_company_ids')
            if 'invitee_ids' in json_data:
                json_data['invitee_ids'] = request.form.getlist('invitee_ids')
                # adding only invitee_ids to collaborators json_data
                c_json_data['invitee_ids'] = json_data['invitee_ids']
            if 'slots' in json_data:
                # if event is non has_slot, so can not add slots in
                # particular event
                if not model.event_sub_type.has_slots:
                    c_abort(422, errors={
                        'slots': ['Event sub type is not has_slot, '
                                  'so you can not add slots']})
                del json_data['slots']
                slot_data = json.loads(request.form['slots'])
            if 'rsvps' in json_data:
                del json_data['rsvps']
                rsvp_data = json.loads(request.form['rsvps'])
            if 'collaborators' in json_data:
                del json_data['collaborators']
                collaborator_data = json.loads(request.form['collaborators'])
            if 'external_invitees' in json_data:
                del json_data['external_invitees']
                external_invitees_data = json.loads(
                    request.form['external_invitees'])
            if 'external_hosts' in json_data:
                del json_data['external_hosts']
                external_host_data = json.loads(
                    request.form['external_hosts'])
            if 'external_participants' in json_data:
                del json_data['external_participants']
                external_participant_data = json.loads(
                    request.form['external_participants'])
            if 'agendas' in json_data:
                del json_data['agendas']
                agenda_data = json.loads(request.form['agendas'])
            if 'cc_emails' in json_data:
                del json_data['cc_emails']
                json_data['cc_emails'] = request.form.getlist('cc_emails')
            if 'account_type_preference' in json_data:
                json_data['account_type_preference'] = request.form.getlist(
                    'account_type_preference')

            if (not json_data and  # <- no text data
                    not attachment['files'] and
                    not invite_logo['files'] and  # no invite_logo upload
                    not invite_banner['files'] and   # no invite_banner upload
                    not audio['files'] and
                    not transcript['files'] and (  # no invite_banner upload
                    'delete' not in invite_logo or  # no invite_logo delete
                    not invite_logo['delete']) and (
                    'delete' not in invite_banner or  # no invite_banner delete
                    not invite_banner['delete']) and (
                    'delete' not in attachment or
                    not attachment['delete']) and (
                    'delete' not in audio or
                    not audio['delete']) and (
                    'delete' not in transcript or
                    not transcript['delete']) and
                    not rsvp_data and not slot_data and  # no external data
                    not collaborator_data and not external_invitees_data and
                    not external_host_data and
                    not external_participant_data and
                    not cae_participant_data):
                # no data of any sort
                c_abort(400)

            # validate and deserialize input
            if collaborator_editor:
                json_data = c_json_data
            data = None
            if json_data:
                data, errors = corporate_access_event_edit_schema.load(
                    json_data, instance=model, partial=True)
                if errors:
                    c_abort(422, errors=errors)
            if not data:
                data = model

            # permission for meeting type events
            if (data.event_type.is_meeting and
                    corporate_access_event_edit_schema.\
                    _cached_meeting_account):
                # get account_type
                meeting_account_type = corporate_access_event_edit_schema.\
                    _cached_meeting_account.account_type
                # if current user type is corporate, private and sme then
                # they can invite only sell-side, buy-side and general investor
                # vice-versa
                if (g.current_user['account_type'] in [
                        ACCOUNT.ACCT_CORPORATE, ACCOUNT.ACCT_SME,
                        ACCOUNT.ACCT_PRIVATE] and
                        meeting_account_type not in [
                        ACCOUNT.ACCT_SELL_SIDE_ANALYST,
                        ACCOUNT.ACCT_BUY_SIDE_ANALYST,
                        ACCOUNT.ACCT_GENERAL_INVESTOR]):
                    c_abort(403)
                elif (g.current_user['account_type'] in [
                        ACCOUNT.ACCT_SELL_SIDE_ANALYST,
                        ACCOUNT.ACCT_BUY_SIDE_ANALYST,
                        ACCOUNT.ACCT_GENERAL_INVESTOR] and
                        meeting_account_type not in [
                        ACCOUNT.ACCT_CORPORATE, ACCOUNT.ACCT_SME,
                        ACCOUNT.ACCT_PRIVATE]):
                    c_abort(403)
            # images upload
            if invite_logo and (invite_logo['files'] or
                                'delete' in invite_logo):
                # parse new files
                if invite_logo['files']:
                    data.invite_logo_filename = [
                        logo_name for logo_name in invite_logo['files']][0]
                # any old files to delete
                if 'delete' in invite_logo:
                    for invite_logo in invite_logo['delete']:
                        if invite_logo == data.invite_logo_filename:
                            data.invite_logo_filename = None
            if invite_banner and (invite_banner['files'] or
                                  'delete' in invite_banner):
                # parse new files
                if invite_banner['files']:
                    data.invite_banner_filename = [
                        banner_name for banner_name in
                        invite_banner['files']][0]
                # any old files to delete
                if 'delete' in invite_banner:
                    for banner_name in invite_banner['delete']:
                        if banner_name == data.invite_banner_filename:
                            data.invite_banner_filename = None
            if attachment and (attachment['files'] or
                               'delete' in attachment):
                # parse new files
                if attachment['files']:
                    data.attachment = [
                        attachment for attachment in
                        attachment['files']][0]
                # any old files to delete
                if 'delete' in attachment:
                    for attachment in attachment['delete']:
                        if attachment == data.attachment:
                            data.attachment = None
            if audio and (audio['files'] or 'delete' in audio):
                # parse new files
                if audio['files']:
                    data.audio_filename = [
                        audio for audio in audio['files']][0]
                # any old files to delete
                if 'delete' in audio:
                    for audio in audio['delete']:
                        if audio == data.audio_filename:
                            data.audio_filename = None
            if transcript and (transcript['files'] or 'delete' in transcript):
                # parse new files
                if transcript['files']:
                    data.transcript_filename = [
                        transcript for transcript in
                        transcript['files']][0]
                # any old files to delete
                if 'delete' in transcript:
                    for transcript_name in transcript['delete']:
                        if transcript_name == data.transcript_filename:
                            data.transcript_filename = None
            # no errors, so update data to db
            if 'launch' in input_data and input_data['launch']:
                data.is_draft = False
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()

            # manage participant companies list
            if (corporate_access_event_edit_schema.
                    _cached_participant_companies or
                    'participant_company_ids' in json_data):
                # add new ones
                for cf in corporate_access_event_edit_schema.\
                        _cached_participant_companies:
                    if cf not in data.caevent_participant_companies:
                        data.caevent_participant_companies.append(cf)
                # remove old ones
                for oldcf in data.caevent_participant_companies[:]:
                    if (oldcf not in
                            corporate_access_event_edit_schema.
                            _cached_participant_companies):
                        data.caevent_participant_companies.remove(oldcf)
                db.session.add(data)
                db.session.commit()

            # manage file list
            if corporate_access_event_edit_schema._cached_files or \
                    'file_ids' in json_data:
                # add new ones
                for cf in corporate_access_event_edit_schema._cached_files:
                    if cf not in data.files:
                        data.files.append(cf)
                # remove old ones
                for oldcf in data.files[:]:
                    if oldcf not in \
                            corporate_access_event_edit_schema._cached_files:
                        data.files.remove(oldcf)
                db.session.add(data)
                db.session.commit()

            # if sequence id change in participant so first all sequence id
            # null for particular CAEvent
            if cae_participant_data or external_participant_data:
                remove_participant_or_rsvp_sequence_id(
                    cae_participant_data=cae_participant_data,
                    external_participant_data=external_participant_data)
            # if cae_participant_data and external_participant_data and
            # same participant user exists in both object so remove from
            # external_participant_data
            if cae_participant_data and external_participant_data:
                unused, external_participant_data = remove_unused_data(
                    cae_participant_data=cae_participant_data,
                    external_participant_data=external_participant_data)
            # manage participants
            if cae_participant_data and not collaborator_editor:
                for cae_pcpt in cae_participant_data:
                    participant_data = None
                    if 'row_id' in cae_pcpt:
                        participant_model = CorporateAccessEventParticipant.\
                            query.get(cae_pcpt['row_id'])
                        if not participant_model:
                            c_abort(404, message='Corporate Access Event '
                                                 'Participant id: %s does'
                                                 ' not exist' %
                                                 str(cae_pcpt['row_id']))
                        participant_data, errors = \
                            CorporateAccessEventParticipantSchema().load(
                                cae_pcpt, instance=participant_model,
                                partial=True)
                        if errors:
                            db.session.rollback()
                            c_abort(422, errors=errors)
                        participant_data.updated_by = g.current_user['row_id']
                    else:
                        # if participant row_id not present, add participant
                        cae_pcpt['corporate_access_event_id'] = data.row_id
                        # validate and deserialize input
                        participant_data, errors = \
                            CorporateAccessEventParticipantSchema().load(
                                cae_pcpt)
                        if errors:
                            db.session.rollback()
                            c_abort(422, errors=errors)
                        # no errors, so add host data to db
                        participant_data.updated_by = g.current_user['row_id']
                        participant_data.created_by = g.current_user['row_id']
                    if participant_data:
                        db.session.add(participant_data)
                db.session.commit()
            # manage external participants
            if external_participant_data and not collaborator_editor:
                ext_model = None
                for ext_part in external_participant_data:
                    ext_data = None
                    if 'row_id' in ext_part:
                        ext_model = CorporateAccessEventParticipant.query.get(
                            ext_part['row_id'])
                        if not ext_model:
                            c_abort(404, message='Corporate Access Event '
                                                 'Participant id: %s does'
                                                 ' not exist' %
                                                 str(ext_part['row_id']))
                        ext_data, errors = \
                            CorporateAccessEventParticipantSchema().load(
                                ext_part, instance=ext_model, partial=True)
                        if errors:
                            db.session.rollback()
                            c_abort(422, errors=errors)
                        ext_data.updated_by = g.current_user['row_id']
                    else:
                        # if participant row_id not present, add participant
                        ext_part['corporate_access_event_id'] = \
                            data.row_id
                        # validate and deserialize input
                        ext_data, errors = \
                            CorporateAccessEventParticipantSchema().load(
                                ext_part)
                        if errors:
                            db.session.rollback()
                            c_abort(422, errors=errors)
                        # no errors, so add host data to db
                        ext_data.updated_by = g.current_user['row_id']
                        ext_data.created_by = g.current_user['row_id']
                    if ext_data:
                        db.session.add(ext_data)
                db.session.commit()
            host_email_ids = []
            # manage hosts
            if (corporate_access_event_edit_schema._cached_host_users or
                    'host_ids' in json_data):
                host_ids = []
                for host in corporate_access_event_edit_schema.\
                        _cached_host_users:
                    # host_email_ids list for check external host is exists in
                    # external host
                    host_email_ids.append(host.email)
                    if host not in data.hosts:
                        host_ids.append(host.row_id)
                        db.session.add(CorporateAccessEventHost(
                            corporate_access_event_id=data.row_id,
                            host_id=host.row_id,
                            created_by=g.current_user['row_id'],
                            updated_by=g.current_user['row_id']))
                # remove old ones
                for oldhost in data.corporate_access_event_hosts[:]:
                    if (oldhost.host not in
                            corporate_access_event_edit_schema.
                            _cached_host_users):
                        if (oldhost.host and
                                oldhost.host.email in host_email_ids):
                            host_email_ids.remove(oldhost.host.email)
                        if oldhost in data.corporate_access_event_hosts:
                            if oldhost.host_id:
                                db.session.delete(oldhost)
                                db.session.commit()
                db.session.commit()
            # manage external hosts
            if external_host_data and not collaborator_editor:
                ext_model = None
                for ext_host in external_host_data:
                    ext_data = None
                    if 'row_id' in ext_host:
                        ext_model = CorporateAccessEventHost.query.get(
                            ext_host['row_id'])
                        if not ext_model:
                            c_abort(404, message='Corporate Access Event '
                                                 'Host id: %s does'
                                                 ' not exist' %
                                                 str(ext_host['row_id']))
                        ext_data, errors = CorporateAccessEventHostSchema(
                        ).load(ext_host, instance=ext_model, partial=True)
                        if errors:
                            db.session.rollback()
                            c_abort(422, errors=errors)
                        ext_data.updated_by = g.current_user['row_id']
                    else:
                        # if host row_id not present, add host
                        ext_host['corporate_access_event_id'] = data.row_id
                        # if same host exists in host_ids so not insert second
                        # time
                        if ext_host['host_email'] in host_email_ids:
                            continue
                        # validate and deserialize input
                        ext_data, errors = CorporateAccessEventHostSchema()\
                            .load(ext_host)
                        if errors:
                            db.session.rollback()
                            c_abort(422, errors=errors)
                        # no errors, so add host data to db
                        ext_data.updated_by = g.current_user['row_id']
                        ext_data.created_by = g.current_user['row_id']
                    if ext_data:
                        db.session.add(ext_data)
                db.session.commit()
            invitee_email_ids = []
            final_invitee_email_ids = []
            # manage invitees
            if (corporate_access_event_edit_schema._cached_contact_users or
                    'invitee_ids' in json_data):
                for invitee in corporate_access_event_edit_schema.\
                        _cached_contact_users:
                    # invitee_email_ids list for check invitee user
                    # exists in external invitee or not
                    invitee_email_ids.append(invitee.email)
                    final_invitee_email_ids.append(invitee.email)
                    if invitee not in data.invitees:
                        invitee_ids.append(invitee.row_id)
                        db.session.add(CorporateAccessEventInvitee(
                            corporate_access_event_id=data.row_id,
                            # directly assign user_id for system user
                            invitee_id=invitee.row_id,
                            user_id=invitee.row_id,
                            created_by=g.current_user['row_id'],
                            updated_by=g.current_user['row_id']))
                # remove old ones
                for oldinvite in data.corporate_access_event_invitees[:]:
                    if oldinvite.created_by != g.current_user['row_id']:
                        # only invitee creator can delete old invite
                        continue
                    if (oldinvite.invitee not in
                            corporate_access_event_edit_schema.
                            _cached_contact_users):
                        if (oldinvite.invitee and
                                oldinvite.invitee.email in invitee_email_ids):
                            invitee_email_ids.remove(
                                oldinvite.invitee.email)
                        if oldinvite in data.corporate_access_event_invitees:
                            if oldinvite.invitee_id:
                                db.session.delete(oldinvite)
                                db.session.commit()
                db.session.commit()
            # manage external invitees
            if external_invitees_data:
                ext_model = None
                for ext_invitee in external_invitees_data:
                    ext_data = None
                    if 'row_id' in ext_invitee:
                        ext_model = CorporateAccessEventInvitee.query.get(
                            ext_invitee['row_id'])
                        if not ext_model:
                            c_abort(404, message='Corporate Access Event '
                                                 'Invitee id: %s does'
                                                 ' not exist' %
                                                 str(ext_invitee['row_id']))
                        ext_invt_old_list.append(ext_model.invitee_email)
                        ext_data, errors = CorporateAccessEventInviteeSchema(
                        ).load(ext_invitee, instance=ext_model, partial=True)
                        if errors:
                            db.session.rollback()
                            c_abort(422, errors=errors)
                        ext_data.updated_by = g.current_user['row_id']
                        ext_invt_update_list.append(ext_data.invitee_email)
                    else:
                        # if invitee row_id not present, add invitee
                        ext_invitee['corporate_access_event_id'] = data.row_id
                        # if same host exists in invitee_ids so not insert
                        # second time
                        if ext_invitee['invitee_email'] in invitee_email_ids:
                            continue
                        # validate and deserialize input
                        ext_data, errors = CorporateAccessEventInviteeSchema()\
                            .load(ext_invitee)
                        if errors:
                            db.session.rollback()
                            c_abort(422, errors=errors)
                        # no errors, so add rsvps data to db
                        user_row_id = check_external_invitee_exists_in_user(
                            ext_data.invitee_email)
                        if user_row_id:
                            ext_data.user_id = user_row_id
                        ext_data.updated_by = g.current_user['row_id']
                        ext_data.created_by = g.current_user['row_id']
                        ext_invt_update_list.append(ext_data.invitee_email)
                    if ext_data:
                        db.session.add(ext_data)
                db.session.commit()
                invitee_list = list(set(ext_invt_update_list) - set(
                    ext_invt_old_list))

            # deleting invitees which are not received
            if external_invitees_data is not None:
                final_invitee_email_ids += ext_invt_update_list
                CorporateAccessEventInvitee.query.filter(and_(
                    CorporateAccessEventInvitee.corporate_access_event_id == data.row_id,
                    CorporateAccessEventInvitee.invitee_email.notin_(
                        final_invitee_email_ids))).delete(synchronize_session=False)
                db.session.commit()

            # manage slots
            if slot_data:
                for slot in slot_data:
                    slts = None
                    if 'row_id' in slot:
                        # if slot found, update the slot
                        slot_model = CorporateAccessEventSlot.query.get(
                            slot['row_id'])
                        if not slot_model:
                            c_abort(404, message='Corporate Access Event '
                                                 'slot id: %s does not exist' %
                                                 str(slot['row_id']))
                        slts, errors = \
                            CorporateAccessEventSlotSchema().load(
                                slot, instance=slot_model, partial=True)
                        if errors:
                            db.session.rollback()
                            c_abort(422, errors=errors)
                        slts.updated_by = g.current_user['row_id']
                    else:
                        # if slot row_id not present, add slot
                        slot['event_id'] = data.row_id
                        # validate and deserialize input
                        slts, errors = CorporateAccessEventSlotSchema().load(
                            slot, partial=True)
                        if errors:
                            c_abort(422, errors=errors)
                        # no errors, so add slots data to db
                        slts.updated_by = g.current_user['row_id']
                        slts.created_by = g.current_user['row_id']
                        slts.account_id = g.current_user['account_id']
                    if slts:
                        db.session.add(slts)
                db.session.commit()
            # manage agenda
            if agenda_data:
                for agenda in agenda_data:
                    agnds = None
                    if 'row_id' in agenda:
                        # if agenda found, update the agenda
                        ageda_model = CorporateAccessEventAgenda.query.get(
                            agenda['row_id'])
                        if not ageda_model:
                            c_abort(404, message='Corporate Access Event '
                                                 'agenda id: %s does not '
                                                 'exist' %
                                                 str(agenda['row_id']))
                        agnds, errors = \
                            CorporateAccessEventAgendaSchema().load(
                                agenda, instance=ageda_model, partial=True)
                        if errors:
                            db.session.rollback()
                            c_abort(422, errors=errors)
                        agnds.updated_by = g.current_user['row_id']
                    else:
                        # if agenda row_id not present, add agenda
                        agenda['corporate_access_event_id'] = data.row_id
                        # validate and deserialize input
                        agnds, errors = CorporateAccessEventAgendaSchema().\
                            load(agenda, partial=True)
                        if errors:
                            c_abort(422, errors=errors)
                        # no errors, so add slots data to db
                        agnds.updated_by = g.current_user['row_id']
                        agnds.created_by = g.current_user['row_id']
                    if agnds:
                        db.session.add(agnds)
                db.session.commit()
            # manage rsvps
            rsvp_model = None
            if rsvp_data:
                remove_participant_or_rsvp_sequence_id(rsvps=rsvp_data)
                for rsvp in rsvp_data:
                    rsvps = None
                    # if rsvp found, update the rsvp
                    if 'row_id' in rsvp:
                        rsvp_model = CorporateAccessEventRSVP.query.get(
                            rsvp['row_id'])
                        if not rsvp_model:
                            c_abort(404, message='Corporate Access Event '
                                                 'RSVP id: %s does not exist' %
                                                 str(rsvp['row_id']))
                        rsvps, errors = \
                            CorporateAccessEventRSVPSchema().load(
                                rsvp, instance=rsvp_model, partial=True)
                        if errors:
                            db.session.rollback()
                            c_abort(422, errors=errors)
                        rsvps.updated_by = g.current_user['row_id']
                    else:
                        # if rsvp row_id not present, add rsvp
                        rsvp['corporate_access_event_id'] = data.row_id
                        # validate and deserialize input
                        rsvps, errors = CorporateAccessEventRSVPSchema().load(
                            rsvp)
                        if errors:
                            c_abort(422, errors=errors)
                        # no errors, so add rsvps data to db
                        rsvps.updated_by = g.current_user['row_id']
                        rsvps.created_by = g.current_user['row_id']
                    if rsvps:
                        db.session.add(rsvps)
                db.session.commit()
            # manage collborators
            coll_model = None
            if collaborator_data and not collaborator_editor:
                for collaborator in collaborator_data:
                    coll_data = None
                    if 'row_id' in collaborator:
                        coll_model = CorporateAccessEventCollaborator.query.\
                            get(collaborator['row_id'])
                        if not coll_model:
                            c_abort(
                                404, message='Corporate Access Event '
                                'Collaborator id: %s does not exist' %
                                str(collaborator['row_id']))
                        coll_data, errors = \
                            CorporateAccessEventCollaboratorSchema().load(
                                collaborator, instance=coll_model,
                                partial=True)
                        if errors:
                            db.session.rollback()
                            c_abort(422, errors=errors)
                        coll_data.updated_by = g.current_user['row_id']
                    else:
                        collaborator['corporate_access_event_id'] = data.row_id
                        coll_data, errors = \
                            CorporateAccessEventCollaboratorSchema().load(
                                collaborator)
                        if errors:
                            db.session.rollback()
                            c_abort(422, errors=errors)
                        coll_data.updated_by = g.current_user['row_id']
                        coll_data.created_by = g.current_user['row_id']
                    if coll_data:
                        db.session.add(coll_data)
                db.session.commit()

            # update the stats table for corporate access event
            update_corporate_event_stats.s(True, data.row_id).delay()

            # send event update emails when rsvps are updated
            rsvp_new_list = []
            for rsvp in data.rsvps:
                rsvp_new_list.append(
                    {rsvp.email: rsvp.contact_person})
            if rsvp_new_list != rsvp_old_list and model.is_draft is False:
                send_corporate_access_event_updated_email.s(
                    True, data.row_id).delay()
                # event update invitee notification
                add_cae_updated_invitee_notification.s(
                    True, data.row_id,
                    NOTIFY.NT_COR_EVENT_UPDATED_INVITEE).delay()
                # event update host notification
                add_cae_updated_host_notification.s(
                    True, data.row_id,
                    NOTIFY.NT_COR_EVENT_UPDATED_HOST).delay()
                # event update collaborator notification
                add_cae_updated_collaborator_notification.s(
                    True, data.row_id,
                    NOTIFY.NT_COR_EVENT_UPDATED_COLLABORATOR).delay()
                # #TODO: used in future
                # event update rsvp notification
                """
                add_cae_updated_rsvp_notification.s(
                    True, data.row_id,
                    NOTIFY.NT_COR_EVENT_UPDATED_RSVP).delay()
                """
                # event update participant notification
                add_cae_updated_participant_notification.s(
                    True, data.row_id,
                    NOTIFY.NT_COR_EVENT_UPDATED_PARTICIPANT).delay()

            # condition for sending emails, if satisfies send emails
            if old_is_draft is True and model.is_draft is False:
                send_corporate_access_event_launch_email.s(
                    True, data.row_id, not_for_creator=False).delay()

                if data.corporate_access_event_invitees:
                    add_cae_invite_added_notification.s(
                        True, data.row_id,
                        NOTIFY.NT_COR_EVENT_INVITED).delay()
                if data.corporate_access_event_hosts:
                    add_cae_host_added_notification.s(
                        True, data.row_id,
                        NOTIFY.NT_COR_HOST_ADDED).delay()
                # #TODO: used in future
                """if data.rsvps:
                    add_cae_rsvp_added_notification.s(
                        True, data.row_id, NOTIFY.NT_COR_RSVP_ADDED).delay()"""

                # participant added
                if data.corporate_access_event_participants:
                    add_cae_participant_added_notification.s(
                        True, data.row_id,
                        NOTIFY.NT_COR_PARTICIPANT_ADDED).delay()
                # collaborator added
                if data.collaborators:
                    add_cae_collaborator_added_notification.s(
                        True, data.row_id,
                        NOTIFY.NT_COR_COLLABORATOR_ADDED).delay()

                # true specifies mail sending task is in queue
                data.is_in_process = True
                db.session.add(data)
                db.session.commit()
            # if any existing external invitee email changed or
            # new external invitee added then send email to invitee.
            if old_is_draft is False and model.is_draft is False:
                if invitee_list or invitee_ids:
                    send_corporate_access_event_new_invitee_email.s(
                        True, data.row_id, invitee_list, invitee_ids).delay()
                    # true specifies mail sending task is in queue
                    data.is_in_process = True
                    db.session.add(data)
                    db.session.commit()

            if ('USE_ELASTIC_SEARCH' in flaskapp.config
                    and flaskapp.config['USE_ELASTIC_SEARCH']):
                add_to_index(APP.DF_ES_INDEX, data)

        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (corporate_access_event_id, collaborator_id) = \
                # (3, 3) already exists.
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
        except HTTPException as e:
            raise e
        except Forbidden as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Updated Corporate Access Event id: %s' %
                str(row_id)}, 200

    @swag_from('swagger_docs/corporate_access_events_delete.yml')
    def delete(self, row_id):
        """
        Delete a Corporate Access Event
        """
        model = None
        try:
            # first find model
            model = CorporateAccessEvent.query.get(row_id)
            if model is None:
                c_abort(404, message='Corporate Access Event '
                        'id: %s does not exist' % str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            if model.is_draft is False:
                c_abort(422, message='Corporate Access Event published,'
                        ' so it cannot be deleted')
            if model.cancelled:
                c_abort(422, message='Corporate Access Event cancelled,'
                        ' so it cannot be deleted')
            db.session.delete(model)
            db.session.commit()
            if ('USE_ELASTIC_SEARCH' in flaskapp.config
                    and flaskapp.config['USE_ELASTIC_SEARCH']):
                remove_from_index(APP.DF_ES_INDEX, model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204

    @swag_from('swagger_docs/corporate_access_events_get.yml')
    def get(self, row_id):
        """
        Get a Corporate Access Event by id
        """
        input_data = None
        event_data = None
        cor_invitee = None
        input_data = parser.parse(
            BaseCommonSchema(), locations=('querystring',))
        # if verify token there, then guest user or normal user booked
        # particular event
        if 'token' in input_data and input_data['token']:
            # verify token
            event_data = verify_event_book_token(
                input_data['token'], APP.EVNT_CA_EVENT)
            if event_data:
                # if current user is guest user
                cor_invitee = CorporateAccessEventInvitee.query.filter(
                    and_(
                        CorporateAccessEventInvitee.
                        corporate_access_event_id == event_data[
                            'event_id'],
                        CorporateAccessEventInvitee.row_id == event_data[
                            'invite_id'],
                        CorporateAccessEventInvitee.user_id.is_(None)
                    )).first()
                if cor_invitee:
                    cor_invitee.user_id = g.current_user['row_id']
                    db.session.add(cor_invitee)
                    db.session.commit()
            else:
                c_abort(422, message='Token invalid', errors={
                    'token': ['Token invalid']})
        model = None
        try:
            # first find model
            invitee_user_ids = []
            collaborator_ids = []
            participant_ids = []
            participant_emails = []
            rsvp_emails = []
            host_ids = []
            host_emails = []
            model = CorporateAccessEvent.query.filter(
                CorporateAccessEvent.row_id == row_id).join(
                    CorporateAccessEventInvitee, and_(
                        CorporateAccessEventInvitee.
                        corporate_access_event_id ==
                        CorporateAccessEvent.row_id,
                    or_(CorporateAccessEventInvitee.invitee_email ==
                        g.current_user['email'],
                        CorporateAccessEventInvitee.user_id ==
                        g.current_user['row_id'])), isouter=True).join(
                CorporateAccessEventCollaborator, and_(
                    CorporateAccessEventCollaborator.
                    corporate_access_event_id ==
                    CorporateAccessEvent.row_id,
                    CorporateAccessEventCollaborator.collaborator_id ==
                    g.current_user['row_id']), isouter=True).join(
                CorporateAccessEventHost, and_(
                    CorporateAccessEventHost.
                    corporate_access_event_id ==
                    CorporateAccessEvent.row_id,
                    or_(CorporateAccessEventHost.host_id ==
                        g.current_user['row_id'],
                        CorporateAccessEventHost.host_email ==
                        g.current_user['email'])), isouter=True).join(
                CorporateAccessEventParticipant, and_(
                    CorporateAccessEventParticipant.
                    corporate_access_event_id ==
                    CorporateAccessEvent.row_id,
                    or_(
                        CorporateAccessEventParticipant.participant_id ==
                        g.current_user['row_id'],
                        CorporateAccessEventParticipant.participant_email ==
                        g.current_user['email'])), isouter=True).join(
                CorporateAccessEventRSVP, and_(
                    CorporateAccessEventRSVP.
                    corporate_access_event_id ==
                    CorporateAccessEvent.row_id,
                    CorporateAccessEventRSVP.email ==
                    g.current_user['email']), isouter=True).options(
                joinedload(CorporateAccessEvent.event_type),
                joinedload(CorporateAccessEvent.event_sub_type),
                contains_eager(CorporateAccessEvent.invited),
                contains_eager(CorporateAccessEvent.collaborated),
                contains_eager(CorporateAccessEvent.hosted),
                contains_eager(CorporateAccessEvent.participated),
                contains_eager(CorporateAccessEvent.rsvped)).first()
            if model is None:
                c_abort(404, message='Corporate Access Event id:'
                        ' %s does not exist' % str(row_id))

            # flag for checking open_meeting preferences for account_type
            # initially set to no match(true)
            not_matching_account_type = True
            # check if meeting is open_to_all then, check for current_user
            # account_type
            if model.open_to_all:
                if (model.account_type_preference and
                            g.current_user['account_type'] in
                        model.account_type_preference):
                    not_matching_account_type = False

            invitee_user_ids = [evnt.user_id for evnt in
                                model.corporate_access_event_invitees]
            collaborator_ids = [evnt.collaborator_id for evnt in
                                model.collaborators]
            participant_ids = [evnt.participant_id for evnt in
                               model.corporate_access_event_participants]
            participant_emails = [evnt.participant_email for evnt in
                                  model.corporate_access_event_participants]
            rsvp_emails = [evnt.email for evnt in model.rsvps]
            host_ids = [evnt.host_id for evnt in
                        model.corporate_access_event_hosts]
            host_emails = [evnt.host_email for evnt in
                           model.corporate_access_event_hosts]
            # if model is there, if current user is not event creator and
            # not collaborator and not host and not participant and not rsvp
            # current user can not book particular event, so 403 error arise
            if ((not model.open_to_all or
                    not_matching_account_type and
                    g.current_user['account_type'] != ACCOUNT.ACCT_GUEST) and
                    model.created_by != g.current_user['row_id'] and
                    g.current_user['row_id'] not in collaborator_ids and
                    g.current_user['row_id'] not in invitee_user_ids and
                    g.current_user['row_id'] not in participant_ids and
                    g.current_user['email'] not in participant_emails and
                    g.current_user['email'] not in rsvp_emails and
                    g.current_user['row_id'] not in host_ids and
                    g.current_user['email'] not in host_emails):
                c_abort(403)

            invitee_emails = [invt.invitee.email if invt.invitee
                              else invt.invitee_email for invt in
                              model.corporate_access_event_invitees]
            participant_emails = [evnt.participant.email if evnt.participant
                                  else evnt.participant_email for evnt in
                                  model.corporate_access_event_participants]
            host_emails = [evnt.host.email if evnt.host else evnt.host_email
                           for evnt in model.corporate_access_event_hosts]
            if (g.current_user['account_type'] == ACCOUNT.ACCT_GUEST and
                    model.open_to_all and
                    g.current_user['email'] not in
                    invitee_emails + participant_emails + host_emails):
                c_abort(404, message='Corporate Access Event id:'
                                     ' %s does not exist.' % str(row_id))
            # some fields need to be display here so removing
            # from _default_exclude_fields list by making a copy
            local_exclude_list = CorporateAccessEventSchema.\
                _default_exclude_fields[:]
            local_exclude_list_remove = [
                'agendas', 'hosts', 'participants', 'invitees',
                'joined_invitees', 'corporate_access_event_participants',
                'corporate_access_event_hosts', 'slots',
                'corporate_access_event_invitees', 'rsvps',
                'corporate_access_event_attendee', 'files', 'city', 'state',
                'country', 'collaborators']
            final_list = list(set(local_exclude_list).difference(
                set(local_exclude_list_remove)))
            include_current_users_groups_only()
            result = CorporateAccessEventSchema(exclude=final_list).dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class CorporateAccessEventNoAuthAPI(BaseResource):

    def get(self, row_id):
        """
        Get a Corporate Access Event by id
        """
        try:
            # first find model
            model = CorporateAccessEvent.query.filter(
                CorporateAccessEvent.row_id == row_id).first()
            if model is None:
                c_abort(404, message='Corporate Access Event id:'
                                     ' %s does not exist' % str(row_id))
            if model.is_draft or not model.open_to_all:
                c_abort(403)

            result = CorporateAccessEventSchema(
                only=CorporateAccessNoAuthSchema._include_only).dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data}, 200


class CorporateAccessEventListAPI(AuthResource):
    """
    Read API for Corporate Access Event lists, i.e, more than 1
    """
    model_class = CorporateAccessEvent

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = [
            'invite_logo_url', 'invite_banner_url', 'audio_url', 'video_url',
            'creator', 'hosts', 'participants', 'slots', 'transcript_url']
        super(CorporateAccessEventListAPI, self).__init__(*args, **kwargs)

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
        event_type_name = None
        company_name = None
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
                elif f == 'event_type_name' and extra_query[f]:
                    event_type_name = extra_query[f]
                elif f == 'company_name' and extra_query[f]:
                    company_name = extra_query[f]
                elif f == 'main_filter':
                    main_filter = extra_query[f]

        # for union query without current_user filter
        query_filters_union = {}
        query_filters_union['base'] = query_filters['base'][:]
        query_filters_union['filters'] = query_filters['filters'][:]
        query_filters_union['base'].append(
            CorporateAccessEvent.is_draft.is_(False))
        query_for_union = self._build_final_query(
            query_filters_union, query_session, operator)

        query_filters['base'].append(or_(
            CorporateAccessEvent.created_by == g.current_user['row_id'],
            and_(g.current_user['account_type'] ==
                 any_(CorporateAccessEvent.account_type_preference),
                 CorporateAccessEvent.is_draft.is_(False),
                 CorporateAccessEvent.open_to_all.is_(True))))

        query = self._build_final_query(query_filters, query_session, operator)

        join_load = [
            # let it know that this is already loaded
            contains_eager(CorporateAccessEvent.invited),
            # event type related stuff
            joinedload(CorporateAccessEvent.event_type),
            # event sub type related stuff
            joinedload(CorporateAccessEvent.event_sub_type),
            # invitees and related stuff
            joinedload(CorporateAccessEvent.invitees, innerjoin=innerjoin),
            # participants and related stuff
            joinedload(CorporateAccessEvent.participants, innerjoin=innerjoin),
            joinedload(CorporateAccessEvent.hosts, innerjoin=innerjoin)]

        if not main_filter == CAEVENT.MNFT_INVITED:
            join_load.extend([
                contains_eager(CorporateAccessEvent.collaborated),
                contains_eager(CorporateAccessEvent.hosted),
                contains_eager(CorporateAccessEvent.participated),
                contains_eager(CorporateAccessEvent.rsvped)])

        # eager load
        query = query.options(*join_load)

        invitee_query = query_for_union.join(
            CorporateAccessEventInvitee, and_(
                (CorporateAccessEventInvitee.
                 corporate_access_event_id ==
                 CorporateAccessEvent.row_id),
                or_(
                    CorporateAccessEventInvitee.invitee_email ==
                    g.current_user['email'],
                    CorporateAccessEventInvitee.user_id ==
                    g.current_user['row_id']
                ))).options(
            *join_load)
        participant_query = query_for_union.join(
            CorporateAccessEventParticipant, and_(
                (CorporateAccessEventParticipant.
                 corporate_access_event_id ==
                 CorporateAccessEvent.row_id),
                or_(
                    CorporateAccessEventParticipant.participant_id ==
                    g.current_user['row_id'],
                    CorporateAccessEventParticipant.participant_email ==
                    g.current_user['email']))).options(
            *join_load)
        collaborator_query = query_for_union.join(
            CorporateAccessEventCollaborator, and_(
                (CorporateAccessEventCollaborator.
                 corporate_access_event_id ==
                 CorporateAccessEvent.row_id),
                (CorporateAccessEventCollaborator.collaborator_id ==
                 g.current_user['row_id']))).options(*join_load)
        host_query = query_for_union.join(
            CorporateAccessEventHost, and_(
                (CorporateAccessEventHost.
                 corporate_access_event_id ==
                 CorporateAccessEvent.row_id),
                or_(CorporateAccessEventHost.host_id ==
                    g.current_user['row_id'],
                    CorporateAccessEventHost.host_email ==
                    g.current_user['email']))).options(*join_load)

        if not main_filter or main_filter == CAEVENT.MNFT_ALL:
            # for showing events current user either created or invited to
            final_query = query.union(
                invitee_query, participant_query, collaborator_query,
                host_query)
            # join for contains eager
            final_query = final_query.join(
                CorporateAccessEventInvitee,
                and_(
                    CorporateAccessEventInvitee.
                    corporate_access_event_id ==
                    CorporateAccessEvent.row_id,
                    or_(
                        CorporateAccessEventInvitee.invitee_id ==
                        g.current_user['row_id'],
                        CorporateAccessEventInvitee.invitee_email ==
                        g.current_user['email'])), isouter=True)
            final_query = final_query.join(
                CorporateAccessEventCollaborator, and_(
                    CorporateAccessEventCollaborator.
                    corporate_access_event_id ==
                    CorporateAccessEvent.row_id,
                    CorporateAccessEventCollaborator.collaborator_id ==
                    g.current_user['row_id']), isouter=True)
            final_query = final_query.join(
                CorporateAccessEventHost, and_(
                    CorporateAccessEventHost.
                    corporate_access_event_id ==
                    CorporateAccessEvent.row_id,
                    or_(CorporateAccessEventHost.host_id ==
                        g.current_user['row_id'],
                        CorporateAccessEventHost.host_email ==
                        g.current_user['email'])), isouter=True)
            final_query = final_query.join(
                CorporateAccessEventParticipant, and_(
                    CorporateAccessEventParticipant.
                    corporate_access_event_id ==
                    CorporateAccessEvent.row_id,
                    or_(
                        CorporateAccessEventParticipant.participant_id ==
                        g.current_user['row_id'],
                        CorporateAccessEventParticipant.participant_email ==
                        g.current_user['email'])), isouter=True)
            final_query = final_query.join(
                CorporateAccessEventRSVP, and_(
                    CorporateAccessEventRSVP.
                    corporate_access_event_id ==
                    CorporateAccessEvent.row_id,
                    CorporateAccessEventRSVP.email ==
                    g.current_user['email']), isouter=True)
        elif main_filter == CAEVENT.MNFT_INVITED:
            # for showing events current user is invited to
            final_query = invitee_query
        elif main_filter == CAEVENT.MNFT_PARTICIPATED:
            # for showing events current user is invited to
            final_query = participant_query
        elif main_filter == CAEVENT.MNFT_HOSTED:
            final_query = host_query
        elif main_filter == CAEVENT.MNFT_COLLABORATED:
            final_query = collaborator_query
        elif main_filter == CAEVENT.MNFT_MINE:
            # for showing only events created by current user
            query_filters['base'].append(
                CorporateAccessEvent.created_by == g.current_user['row_id'])
            query = self._build_final_query(
                query_filters, query_session, operator)
            final_query = query.options(*join_load)
            # join for event invited
            final_query = final_query.join(
                CorporateAccessEventInvitee,
                and_(
                    CorporateAccessEventInvitee.
                    corporate_access_event_id ==
                    CorporateAccessEvent.row_id,
                or_(CorporateAccessEventInvitee.invitee_email ==
                    g.current_user['email'],
                    CorporateAccessEventInvitee.user_id ==
                    g.current_user['row_id'])), isouter=True)
            # join for event collaborated
            final_query = final_query.join(
                CorporateAccessEventCollaborator, and_(
                    CorporateAccessEventCollaborator.
                    corporate_access_event_id ==
                    CorporateAccessEvent.row_id,
                    CorporateAccessEventCollaborator.collaborator_id ==
                    g.current_user['row_id']), isouter=True)
            final_query = final_query.join(
                CorporateAccessEventHost, and_(
                    CorporateAccessEventHost.
                    corporate_access_event_id ==
                    CorporateAccessEvent.row_id,
                    or_(CorporateAccessEventHost.host_id ==
                        g.current_user['row_id'],
                        CorporateAccessEventHost.host_email ==
                        g.current_user['email'])), isouter=True)
            final_query = final_query.join(
                CorporateAccessEventParticipant, and_(
                    CorporateAccessEventParticipant.
                    corporate_access_event_id ==
                    CorporateAccessEvent.row_id,
                    or_(
                        CorporateAccessEventParticipant.participant_id ==
                        g.current_user['row_id'],
                        CorporateAccessEventParticipant.participant_email ==
                        g.current_user['email'])), isouter=True)
            final_query = final_query.join(
                CorporateAccessEventRSVP, and_(
                    CorporateAccessEventRSVP.
                    corporate_access_event_id ==
                    CorporateAccessEvent.row_id,
                    CorporateAccessEventRSVP.email ==
                    g.current_user['email']), isouter=True)
        if event_type_name:
            final_query = final_query.join(
                CARefEventType, CARefEventType.row_id ==
                CorporateAccessEvent.event_type_id).filter(
                func.lower(CARefEventType.name).like(
                    '%' + event_type_name.lower() + '%'))
        if company_name:
            final_query = final_query.join(
                Account, Account.row_id ==
                CorporateAccessEvent.account_id).filter(
                func.lower(Account.account_name).like(
                    '%' + company_name.lower() + '%'))

        if sort:
            for col in sort['sort_by']:
                if col == 'event_type_name':
                    col = 'name'
                    mapper = inspect(CARefEventSubType)
                    final_query = final_query.join(
                        CARefEventSubType,
                        CorporateAccessEvent.event_sub_type_id ==
                        CARefEventSubType.row_id)
                elif col == 'company_name':
                    col = 'account_name'
                    mapper = inspect(Account)
                    final_query = final_query.join(
                        Account,
                        Account.row_id == CorporateAccessEvent.account_id)
                else:
                    continue
                sort_fxn = 'asc'
                if sort['sort'] == 'dsc':
                    sort_fxn = 'desc'
                order.append(getattr(mapper.columns[col], sort_fxn)())

        return final_query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/corporate_access_events_get_list.yml')
    def get(self):
        """
        Get the list
        """
        corporate_access_event_read_schema = \
            CorporateAccessEventReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            corporate_access_event_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(
                    filters, pfields, sort, pagination, db.session.query(
                        CorporateAccessEvent), operator)
            # making a copy of the main output schema
            corporate_access_event_schema = CorporateAccessEventSchema(
                exclude=CorporateAccessEventSchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                corporate_access_event_schema = CorporateAccessEventSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching corporate access '
                        'event found')
            result = corporate_access_event_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            abort(500)
        return {'results': result.data, 'total': total}, 200


class CorporateAccessEventNoAuthListAPI(BaseResource):
    """
    Read API for Corporate Access Event lists, i.e, more than 1
    """
    model_class = CorporateAccessEvent

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = [
            'invite_logo_url', 'invite_banner_url', 'audio_url', 'video_url',
            'creator', 'hosts', 'participants', 'slots', 'transcript_url']
        super(CorporateAccessEventNoAuthListAPI, self).__init__(*args, **kwargs)

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
        event_type_name = None
        company_name = None
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
                elif f == 'event_type_name' and extra_query[f]:
                    event_type_name = extra_query[f]
                elif f == 'company_name' and extra_query[f]:
                    company_name = extra_query[f]
                elif f == 'main_filter':
                    main_filter = extra_query[f]

        query_filters['base'].extend([
            CorporateAccessEvent.is_draft.is_(False),
            CorporateAccessEvent.open_to_all.is_(True)]
            )

        query = self._build_final_query(query_filters, query_session, operator)

        join_load = [
            # event type related stuff
            joinedload(CorporateAccessEvent.event_type),
            # event sub type related stuff
            joinedload(CorporateAccessEvent.event_sub_type)]

        # eager load
        final_query = query.options(*join_load)
        if event_type_name:
            final_query = query.join(
                CARefEventType, CARefEventType.row_id ==
                CorporateAccessEvent.event_type_id).filter(
                func.lower(CARefEventType.name).like(
                    '%' + event_type_name.lower() + '%'))
        if company_name:
            final_query = final_query.join(
                Account, Account.row_id ==
                CorporateAccessEvent.account_id).filter(
                func.lower(Account.account_name).like(
                    '%' + company_name.lower() + '%'))

        if sort:
            for col in sort['sort_by']:
                if col == 'event_type_name':
                    col = 'name'
                    mapper = inspect(CARefEventSubType)
                    final_query = final_query.join(
                        CARefEventSubType,
                        CorporateAccessEvent.event_sub_type_id ==
                        CARefEventSubType.row_id)
                elif col == 'company_name':
                    col = 'account_name'
                    mapper = inspect(Account)
                    final_query = final_query.join(
                        Account,
                        Account.row_id == CorporateAccessEvent.account_id)
                else:
                    continue
                sort_fxn = 'asc'
                if sort['sort'] == 'dsc':
                    sort_fxn = 'desc'
                order.append(getattr(mapper.columns[col], sort_fxn)())

        return final_query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/corporate_access_events_get_list.yml')
    def get(self):
        """
        Get the list
        """
        corporate_access_event_read_schema = \
            CorporateAccessEventReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            corporate_access_event_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(
                    filters, pfields, sort, pagination, db.session.query(
                        CorporateAccessEvent), operator)
            db_projection += CorporateAccessNoAuthSchema._include_only
            # making a copy of the main output schema
            corporate_access_event_schema = CorporateAccessNoAuthSchema(
                only=db_projection+['account.account_name']
            )
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                corporate_access_event_schema = CorporateAccessNoAuthSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching corporate access '
                        'event found')
            result = corporate_access_event_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            abort(500)
        return {'results': result.data, 'total': total}, 200


class CorporateAccessEventCancelledAPI(AuthResource):
    """
    API for maintaining Corporate Access Event cancelled feature
    """

    @swag_from('swagger_docs/corporate_access_events_cancel_put.yml')
    def put(self, row_id):
        """
        Update a Corporate Access Event cancelled
        """
        # first find model
        model = None
        try:
            model = CorporateAccessEvent.query.get(row_id)
            if model is None:
                c_abort(404, message='Corporate Access Event id: %s'
                        'does not exist' % str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            if model.is_draft:
                c_abort(422, message="In draft mode, can't be cancelled")
            if not model.cancelled:
                model.cancelled = True
                db.session.add(model)
                db.session.commit()
                send_corporate_access_event_cancellation_email.s(
                    True, row_id).delay()
                add_cae_cancelled_invitee_notification.s(
                    True, row_id,
                    NOTIFY.NT_COR_EVENT_CANCELLED).delay()
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Cancelled Corporate Access Event id: %s' %
                str(row_id)}, 200


class ReSendMailToCAEventInvitee(AuthResource):
    """
    Resend mail to all invitee which have not sent when event launch
    """
    def put(self, row_id):
        """
        Call task for resend mail for particular event
        :param row_id: id of CAevent
        :return:
        """
        # first find model
        model = None
        try:
            model = CorporateAccessEvent.query.get(row_id)
            if model is None:
                c_abort(404, message='Corporate Access Event id: %s'
                                     'does not exist' % str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            if model.is_draft:
                c_abort(422, message="In draft mode, can't be cancelled")
            if model.is_in_process :
                c_abort(422, message="Already processing")

            send_corporate_access_event_launch_email.s(
                True, row_id, not_for_creator=True).delay()

            # true specifies mail sending task is in queue
            model.is_in_process = True
            db.session.add(model)
            db.session.commit()
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Resent mail to Access Event id: %s' %
                           str(row_id)}, 200
