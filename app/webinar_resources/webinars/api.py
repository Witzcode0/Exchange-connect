"""
API endpoints for "webinars" package.
"""

from datetime import datetime as dt

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g, json
from flask_restful import abort
from webargs.flaskparser import parser
from sqlalchemy.exc import IntegrityError
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import load_only, joinedload, contains_eager
from sqlalchemy import and_, any_, or_
from flasgger.utils import swag_from

from app import (
    db, c_abort, webinarinvitelogofile, webinarinvitebannerfile)
from app.base.api import AuthResource, BaseResource
from app.base import constants as APP
from app.base.schemas import BaseCommonSchema
from app.common.helpers import (
    store_file, delete_files, add_update_conference, delete_conference)
from app.webinar_resources.webinars.models import Webinar
from app.webinar_resources.webinars.schemas import (
    WebinarSchema, WebinarReadArgsSchema, PublicWebinarSchema,
    PublishRecordingReadArgSchema)
from app.webcast_resources.webcasts.models import Webcast
from app.common.utils import calling_bigmarker_apis
from app.webinar_resources.webinars.helpers import (
    remove_unused_data, remove_participant_or_rsvp_sequence_id,
    pre_registration_user_for_conference)
from app.webinar_resources.webinar_participants.models import \
    WebinarParticipant
from app.webinar_resources.webinar_hosts.models import WebinarHost
from app.webinar_resources.webinar_invitees.models import WebinarInvitee
from app.webinar_resources.webinar_rsvps.schemas import WebinarRSVPSchema
from app.webinar_resources.webinar_rsvps.models import WebinarRSVP
from app.webinar_resources.webinar_invitees.schemas import \
    WebinarInviteeSchema
from app.webinar_resources.webinar_participants.schemas import \
    WebinarParticipantSchema
from app.webinar_resources.webinar_hosts.schemas import WebinarHostSchema
from app.webinar_resources.webinar_stats.models import WebinarStats
from app.webinar_resources.webinars import constants as WEBINAR
from app.resources.accounts import constants as ACCOUNT
from app.resources.notifications import constants as NOTIFY
from app.resources.roles import constants as ROLE
from app.domain_resources.domains.helpers import (
    get_domain_info, get_domain_name)
from app.resources.users.helpers import include_current_users_groups_only

from queueapp.webinars.stats_tasks import update_webinar_stats
from queueapp.webinars.request_tasks import (
    get_webinar_conference_attendees_list)
from queueapp.webinars.email_tasks import (
    send_webinar_launch_email, send_webinar_completion_email,
    send_webinar_reminder_email, send_webinar_update_email,
    send_webinar_cancellation_email, send_webinar_event_new_invitee_email)
from queueapp.webinars.notification_tasks import (
    add_webinar_invite_notification,
    add_webinar_host_added_notification,
    add_webinar_participant_added_notification,
    add_webinar_rsvp_added_notification,
    add_webinar_updated_host_notification,
    add_webinar_updated_invitee_notification,
    add_webinar_updated_participant_notification,
    add_webinar_updated_participant_notification,
    add_webinar_cancelled_invitee_notification)


class WebinarAPI(AuthResource):
    """
    CRUD API for managing Webinar
    """

    @swag_from('swagger_docs/webinar_post.yml')
    def post(self):
        """
        Create a Webinar
        """
        webinar_schema = WebinarSchema()
        # get the form data from the request
        input_data = None
        input_data = parser.parse(
            BaseCommonSchema(), locations=('querystring',))
        json_data = request.form.to_dict()
        invitee_ids = []
        host_ids = []
        if 'webinar_participants' in json_data:
            json_data['webinar_participants'] = json.loads(request.form[
                'webinar_participants'])
        if 'host_ids' in json_data:
            json_data['host_ids'] = request.form.getlist('host_ids')
        if 'invitee_ids' in json_data:
            json_data['invitee_ids'] = request.form.getlist('invitee_ids')
        if 'open_to_account_types' in json_data:
            json_data['open_to_account_types'] = request.form.getlist(
                'open_to_account_types')
        if 'rsvps' in json_data:
            json_data['rsvps'] = json.loads(request.form['rsvps'])
        if 'external_invitees' in json_data:
            json_data['external_invitees'] = json.loads(request.form[
                'external_invitees'])
        if 'external_participants' in json_data:
            json_data['external_participants'] = json.loads(request.form[
                'external_participants'])
        if 'external_hosts' in json_data:
            json_data['external_hosts'] = json.loads(request.form[
                'external_hosts'])
        if 'file_ids' in json_data:
            json_data['file_ids'] = request.form.getlist('file_ids')
        if 'cc_emails' in json_data:
            json_data['cc_emails'] = request.form.getlist('cc_emails')

        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            # remove all files when come as string
            json_data, unused = remove_unused_data(json_data=json_data)
            is_admin = False
            if ('Origin' in request.headers
                and 'admin' in request.headers['Origin']):
                is_admin = True
            if not is_admin:
                domain_name = get_domain_name()
                domain_id, domain_conf = get_domain_info(domain_name)
                json_data['domain_id'] = domain_id
            data, errors = webinar_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            # if webinar is open to public and current user is not admin
            # open to public webinar only admin can create
            if (data.open_to_public and
                    ACCOUNT.ACCT_ADMIN != g.current_user['account_type']):
                c_abort(403)

            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.account_id = g.current_user['account_id']
            data.updated_by = data.created_by
            data.stats = WebinarStats()
            if data.webinar_participants:
                for web_participant in data.webinar_participants:
                    web_participant.created_by = g.current_user['row_id']
                    web_participant.updated_by = g.current_user['row_id']
            if data.rsvps:
                for rsvp in data.rsvps:
                    rsvp.created_by = g.current_user['row_id']
                    rsvp.updated_by = g.current_user['row_id']
            if data.external_invitees:
                for external_invitee in data.external_invitees:
                    external_invitee.created_by = g.current_user['row_id']
                    external_invitee.updated_by = g.current_user['row_id']
            if data.external_participants:
                for external_participant in data.external_participants:
                    external_participant.created_by = g.current_user['row_id']
                    external_participant.updated_by = g.current_user['row_id']
            if data.external_hosts:
                for external_host in data.external_hosts:
                    external_host.created_by = g.current_user['row_id']
                    external_host.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()
            # manage files list
            if webinar_schema._cached_files:
                for cf in webinar_schema._cached_files:
                    if cf not in data.files:
                        data.files.append(cf)
            db.session.add(data)
            db.session.commit()
            # manage hosts
            if webinar_schema._cached_host_users:
                host_ids = []
                for host in webinar_schema._cached_host_users:
                    if host not in data.hosts:
                        db.session.add(WebinarHost(
                            webinar_id=data.row_id,
                            host_id=host.row_id,
                            created_by=data.created_by,
                            updated_by=data.created_by))
                        host_ids.append(host.row_id)
                db.session.commit()
            # manage invitees
            if webinar_schema._cached_contact_users:
                for invitee in webinar_schema._cached_contact_users:
                    if invitee not in data.invitees:
                        db.session.add(WebinarInvitee(
                            webinar_id=data.row_id,
                            invitee_id=invitee.row_id,
                            created_by=data.created_by,
                            updated_by=data.created_by))
                        invitee_ids.append(invitee.row_id)
                db.session.commit()
            # update webinar stats
            update_webinar_stats.s(True, data.row_id).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (webinar_id, participant_email)=(193, tes@gmail.com)
                # already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (host_id)=(25) is not present in table "user".
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
        sub_folder = data.file_subfolder_name()
        invite_logo_full_folder = data.full_folder_path(
            Webinar.root_invite_logo_folder)
        invite_banner_full_folder = data.full_folder_path(
            Webinar.root_invite_banner_folder)
        # #TODO: audio video used in future

        if 'invite_logo_filename' in request.files:
            logo_path, logo_name, ferrors = store_file(
                webinarinvitelogofile, request.files['invite_logo_filename'],
                sub_folder=sub_folder, full_folder=invite_logo_full_folder)
            if ferrors:
                db.session.delete(data)
                db.session.commit()
                return ferrors['message'], ferrors['code']
            invite_logo['files'][logo_name] = logo_path
        if 'invite_banner_filename' in request.files:
            banner_path, banner_name, ferrors = store_file(
                webinarinvitebannerfile,
                request.files['invite_banner_filename'],
                sub_folder=sub_folder, full_folder=invite_banner_full_folder)
            if ferrors:
                db.session.delete(data)
                db.session.commit()
                return ferrors['message'], ferrors['code']
            invite_banner['files'][banner_name] = banner_path

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
            if 'launch' in input_data and input_data['launch']:
                data.is_draft = False

            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()

            if data.is_draft is False:
                response = add_update_conference(data)
                if not response['status']:
                    db.session.delete(data)
                    db.session.commit()
                    c_abort(422, message='problem with bigmarker',
                            errors=response['response'].get('error', {}))
                if response['conference_id']:
                    pre_registration_user_for_conference(webinar=data)
                    # condition for sending emails, if satisfies send emails
                    send_webinar_launch_email.s(True, data.row_id).delay()
                    if data.webinar_invitees or data.external_invitees:
                        add_webinar_invite_notification.s(
                            True, data.row_id, NOTIFY.NT_WEBINAR_INVITED
                        ).delay()
                    # add host
                    if data.webinar_hosts or data.external_hosts:
                        add_webinar_host_added_notification.s(
                            True, data.row_id, NOTIFY.NT_WEBINAR_HOST_ADDED
                        ).delay()
                    # add participant
                    if data.webinar_participants or data.external_participants:
                        add_webinar_participant_added_notification.s(
                            True, data.row_id,
                            NOTIFY.NT_WEBINAR_PARTICIPANT_ADDED).delay()
                    # uncomment this part for rsvp added notification
                    """
                    # add rsvp
                    if data.rsvps:
                        add_webinar_rsvp_added_notification.s(
                            True, data.row_id,
                            NOTIFY.NT_WEBINAR_RSVP_ADDED).delay()
                    """
                    # true specifies mail sending task is in queue
                    data.is_in_process = True
                    db.session.add(data)
                    db.session.commit()
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            db.session.delete(data)
            db.session.commit()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Webinar added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @swag_from('swagger_docs/webinar_put.yml')
    def put(self, row_id):
        """
        Update a Webinar
        """
        webinar_schema = WebinarSchema()
        # first find model
        model = None
        try:
            # get data from query string using parsing
            input_data = None
            input_data = parser.parse(
                BaseCommonSchema(), locations=('querystring',))
            model = Webinar.query.get(row_id)
            if model is None:
                c_abort(404, message='Webinar id:'
                        '%s does not exist' % str(row_id))
            # is_draft status, to be used for sending email for webinar launch
            old_is_draft = model.is_draft
            old_started_at, old_ended_at = model.started_at, model.ended_at
            rsvp_old_list = []
            for rsvp_old in model.rsvps:
                rsvp_old_list.append(
                    {rsvp_old.email: rsvp_old.contact_person})
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
        except HTTPException as e:
            raise e
        except Exception as e:
            abort(500)

        invite_logo = {'files': {}}
        invite_banner = {'files': {}}
        sub_folder = model.file_subfolder_name()
        invite_logo_full_folder = model.full_folder_path(
            Webinar.root_invite_logo_folder)
        invite_banner_full_folder = model.full_folder_path(
            Webinar.root_invite_banner_folder)

        if 'invite_logo_filename' in request.files:
            logo_path, logo_name, ferrors = store_file(
                webinarinvitelogofile, request.files['invite_logo_filename'],
                sub_folder=sub_folder, full_folder=invite_logo_full_folder)
            if ferrors:
                return ferrors['message'], ferrors['code']
            invite_logo['files'][logo_name] = logo_path
        if 'invite_banner_filename' in request.files:
            banner_path, banner_name, ferrors = store_file(
                webinarinvitebannerfile,
                request.files['invite_banner_filename'],
                sub_folder=sub_folder, full_folder=invite_banner_full_folder)
            if ferrors:
                return ferrors['message'], ferrors['code']
            invite_banner['files'][banner_name] = banner_path

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

        try:
            # get the json data from the request
            json_data = request.form.to_dict()
            invitee_ids = []
            webinar_participant_data = None
            if 'webinar_participants' in json_data:
                del json_data['webinar_participants']
                webinar_participant_data = json.loads(
                    request.form['webinar_participants'])
            if 'participant_ids' in json_data:
                json_data['participant_ids'] = request.form.getlist(
                    'participant_ids')
            if 'host_ids' in json_data:
                json_data['host_ids'] = request.form.getlist('host_ids')
            if 'invitee_ids' in json_data:
                json_data['invitee_ids'] = request.form.getlist('invitee_ids')
            if 'file_ids' in json_data:
                json_data['file_ids'] = request.form.getlist('file_ids')
            if 'open_to_account_types' in json_data:
                del json_data['open_to_account_types']
                json_data['open_to_account_types'] = request.form.getlist(
                    'open_to_account_types')
            rsvp_data = None  # for rsvp data
            if 'rsvps' in json_data:
                del json_data['rsvps']
                rsvp_data = json.loads(request.form['rsvps'])
            external_invitee_data = None  # for external invitee data
            if 'external_invitees' in json_data:
                del json_data['external_invitees']
                external_invitee_data = json.loads(request.form[
                    'external_invitees'])
            external_participant_data = None  # for external participant data
            if 'external_participants' in json_data:
                del json_data['external_participants']
                external_participant_data = json.loads(request.form[
                    'external_participants'])
            external_host_data = None  # for external host data
            if 'external_hosts' in json_data:
                del json_data['external_hosts']
                external_host_data = json.loads(request.form['external_hosts'])
            if 'cc_emails' in json_data:
                del json_data['cc_emails']
                json_data['cc_emails'] = request.form.getlist('cc_emails')

            if (not json_data and  # <- no text data
                    not invite_logo['files'] and  # <- no invite_logo upload
                    not invite_banner['files'] and (  # no invite_banner upload
                    'delete' not in invite_logo or  # no invite_logo delete
                    not invite_logo['delete']) and (
                    'delete' not in invite_banner or  # no invite_banner delete
                    not invite_banner['delete']) and
                    not webinar_participant_data and  # no participants
                    not external_host_data and  # no external host
                    not external_participant_data and  # no ext participants
                    not external_invitee_data and  # no external invitee
                    not rsvp_data):  # no rsvp
                # no data of any sort
                c_abort(400)
            # validate and deserialize input
            data = None
            if json_data:
                data, errors = webinar_schema.load(
                    json_data, instance=model, partial=True)
                if errors:
                    c_abort(422, errors=errors)
            if not data:
                data = model
            # images upload
            if invite_logo and (
                    invite_logo['files'] or 'delete' in invite_logo):
                # parse new files
                if invite_logo['files']:
                    data.invite_logo_filename = [
                        logo_name for logo_name in invite_logo['files']][0]
                # any old files to delete
                if 'delete' in invite_logo:
                    for invite_logo in invite_logo['delete']:
                        if invite_logo == data.invite_logo_filename:
                            data.invite_logo_filename = None
            if invite_banner and (
                    invite_banner['files'] or 'delete' in invite_banner):
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
            if 'launch' in input_data and input_data['launch']:
                data.is_draft = False
            # no errors, so update data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()
            # manage file list
            if webinar_schema._cached_files or 'file_ids' in json_data:
                # add new ones
                for cf in webinar_schema._cached_files:
                    if cf not in data.files:
                        data.files.append(cf)
                # remove old ones
                for oldcf in data.files[:]:
                    if oldcf not in webinar_schema._cached_files:
                        data.files.remove(oldcf)
                db.session.add(data)
                db.session.commit()
            # when webinar_participant_data or external_participant_data
            # remove participant sequence ids for update
            if external_participant_data or webinar_participant_data:
                remove_participant_or_rsvp_sequence_id(
                    webinar_participant_data=external_participant_data,
                    external_participant_data=external_participant_data)
                # if webinar_participant_data and external_participant_data and
                # same participant user exists in both object so remove from
                # external_participant_data
                if webinar_participant_data and external_participant_data:
                    unused, external_participant_data = remove_unused_data(
                        webinar_participant_data=webinar_participant_data,
                        external_participant_data=external_participant_data)
            # # manage participants for system user with sequence_id
            if webinar_participant_data:
                webinar_participant = None
                # if webinar_participant found,
                # update the webinar_participant
                for web_pcpt in webinar_participant_data:
                    if 'row_id' in web_pcpt:
                        web_pcpt_model = \
                            WebinarParticipant.query.get(
                                web_pcpt['row_id'])
                        if not web_pcpt_model:
                            c_abort(404,
                                    message='Webinar Participant id: %s does '
                                            'not exist' % str(
                                                web_pcpt['row_id']))
                        webinar_participant, errors = \
                            WebinarParticipantSchema().load(
                                web_pcpt, instance=web_pcpt_model,
                                partial=True)
                        if errors:
                            db.session.rollback()
                            c_abort(422, errors=errors)
                        webinar_participant.updated_by = g.current_user[
                            'row_id']
                    else:
                        # if webinar_participant row_id not present,
                        # add webinar_participant
                        web_pcpt['webinar_id'] = data.row_id
                        # validate and deserialize input
                        webinar_participant, errors = \
                            WebinarParticipantSchema().load(
                                web_pcpt)
                        if errors:
                            c_abort(422, errors=errors)
                        # no errors, so add external_participants data to db
                        webinar_participant.updated_by = g.current_user[
                            'row_id']
                        webinar_participant.created_by = g.current_user[
                            'row_id']
                    if webinar_participant:
                        db.session.add(webinar_participant)
                db.session.commit()
            # manage external participants
            external_participant_model = None
            if external_participant_data:
                for external_participant in external_participant_data:
                    external_participants = None
                    # if external_participant found,
                    # update the external_participant
                    if 'row_id' in external_participant:
                        external_participant_model = \
                            WebinarParticipant.query.get(
                                external_participant['row_id'])
                        if not external_participant_model:
                            c_abort(
                                404, message='Webinar Participant id: %s does '
                                'not exist' % str(external_participant[
                                    'row_id']))
                        external_participants, errors = \
                            WebinarParticipantSchema().load(
                                external_participant,
                                instance=external_participant_model,
                                partial=True)
                        if errors:
                            db.session.rollback()
                            c_abort(422, errors=errors)
                        external_participants.updated_by = g.current_user[
                            'row_id']
                    else:
                        # if external_participant row_id not present,
                        # add external_participant
                        external_participant['webinar_id'] = data.row_id
                        # validate and deserialize input
                        external_participants, errors = \
                            WebinarParticipantSchema().load(
                                external_participant)
                        if errors:
                            c_abort(422, errors=errors)
                        # no errors, so add external_participants data to db
                        external_participants.updated_by = g.current_user[
                            'row_id']
                        external_participants.created_by = g.current_user[
                            'row_id']
                    if external_participants:
                        db.session.add(external_participants)
                db.session.commit()
            # manage hosts
            host_email_ids = []
            if webinar_schema._cached_host_users or 'host_ids' in json_data:
                host_ids = []
                for host in webinar_schema._cached_host_users:
                    # host_email_ids list for check external host is exists in
                    # external host
                    host_email_ids.append(host.email)
                    if host not in data.hosts:
                        host_ids.append(host.row_id)
                        db.session.add(WebinarHost(
                            webinar_id=data.row_id,
                            host_id=host.row_id,
                            created_by=g.current_user['row_id'],
                            updated_by=g.current_user['row_id']))
                # remove old ones
                for oldhost in data.webinar_hosts[:]:
                    if oldhost.host not in webinar_schema._cached_host_users:
                        if (oldhost.host and
                                oldhost.host.email in host_email_ids):
                            host_email_ids.remove(oldhost.host.email)
                        if oldhost in data.webinar_hosts:
                            if oldhost.host_id:
                                db.session.delete(oldhost)
                                db.session.commit()
                db.session.commit()
            # manage invitees
            final_invitee_email_ids = []
            invitee_email_ids = []
            if (webinar_schema._cached_contact_users or
                    'invitee_ids' in json_data):
                for invitee in webinar_schema._cached_contact_users:
                    # invitee_email_ids list for check invitee user
                    # exists in external invitee or not
                    invitee_email_ids.append(invitee.email)
                    final_invitee_email_ids.append(invitee.email)
                    if invitee not in data.invitees:
                        invitee_ids.append(invitee.row_id)
                        db.session.add(WebinarInvitee(
                            webinar_id=data.row_id,
                            invitee_id=invitee.row_id,
                            created_by=g.current_user['row_id'],
                            updated_by=g.current_user['row_id']))
                # remove old ones
                for oldinvite in data.webinar_invitees[:]:
                    if (oldinvite.invitee not in
                            webinar_schema._cached_contact_users):
                        if (oldinvite.invitee and
                                oldinvite.invitee.email in invitee_email_ids):
                            invitee_email_ids.remove(
                                oldinvite.invitee.email)
                        if oldinvite in data.webinar_invitees:
                            if oldinvite.invitee_id:
                                db.session.delete(oldinvite)
                                db.session.commit()
                db.session.commit()
            # manage rsvps
            rsvp_model = None
            if rsvp_data:
                remove_participant_or_rsvp_sequence_id(rsvps=rsvp_data)
                for rsvp in rsvp_data:
                    rsvps = None
                    # if rsvp found, update the rsvp
                    if 'row_id' in rsvp:
                        rsvp_model = WebinarRSVP.query.get(
                            rsvp['row_id'])
                        if not rsvp_model:
                            c_abort(404, message='Webinar RSVP id: %s does '
                                    'not exist' % str(rsvp['row_id']))
                        rsvps, errors = WebinarRSVPSchema().load(
                            rsvp, instance=rsvp_model, partial=True)
                        if errors:
                            db.session.rollback()
                            c_abort(422, errors=errors)
                        rsvps.updated_by = g.current_user['row_id']
                    else:
                        # if rsvp row_id not present, add rsvp
                        rsvp['webinar_id'] = data.row_id
                        # validate and deserialize input
                        rsvps, errors = WebinarRSVPSchema().load(rsvp)
                        if errors:
                            c_abort(422, errors=errors)
                        # no errors, so add rsvps data to db
                        rsvps.updated_by = g.current_user['row_id']
                        rsvps.created_by = g.current_user['row_id']
                    if rsvps:
                        db.session.add(rsvps)
                db.session.commit()
            # manage external invitees
            external_invitee_model = None
            new_invitee_emails = []
            if external_invitee_data:
                for external_invitee in external_invitee_data:
                    external_invitees = None
                    # if external_invitee found, update the external_invitee
                    if 'row_id' in external_invitee:
                        external_invitee_model = WebinarInvitee.query.get(
                            external_invitee['row_id'])
                        if not external_invitee_model:
                            c_abort(404,
                                    message='Webinar Invitee id: %s does not'
                                    ' exist' % str(external_invitee['row_id']))
                        external_invitees, errors = \
                            WebinarInviteeSchema().load(
                                external_invitee,
                                instance=external_invitee_model, partial=True)
                        if errors:
                            db.session.rollback()
                            c_abort(422, errors=errors)
                        external_invitees.updated_by = g.current_user['row_id']
                        final_invitee_email_ids.append(
                            external_invitees.invitee_email)
                    else:
                        # if external_invitee row_id not present,
                        # add external_invitee
                        external_invitee['webinar_id'] = data.row_id
                        # if same host exists in invitee_ids so not insert
                        # second time
                        if (external_invitee['invitee_email'] in
                                invitee_email_ids):
                            continue
                        if WebinarInvitee.query.filter(and_(
                                WebinarInvitee.invitee_email ==
                                external_invitee['invitee_email'],
                                WebinarInvitee.webinar_id == data.row_id)
                                ).first():
                            continue
                        # validate and deserialize input
                        external_invitees, errors = \
                            WebinarInviteeSchema().load(external_invitee)
                        if errors:
                            c_abort(422, errors=errors)
                        # no errors, so add external_invitees data to db
                        external_invitees.updated_by = g.current_user['row_id']
                        external_invitees.created_by = g.current_user['row_id']
                        new_invitee_emails.append(
                            external_invitees.invitee_email)
                    if external_invitees:
                        db.session.add(external_invitees)
                db.session.commit()

            # deleting invitees which are not received
            if external_invitee_data is not None:
                final_invitee_email_ids += new_invitee_emails
                WebinarInvitee.query.filter(and_(
                    WebinarInvitee.webinar_id == data.row_id,
                    WebinarInvitee.invitee_email.notin_(
                        final_invitee_email_ids))).delete(
                    synchronize_session=False)
                db.session.commit()

            # manage external hosts
            external_host_model = None
            if external_host_data:
                for external_host in external_host_data:
                    external_hosts = None
                    # if external_host found, update the external_host
                    if 'row_id' in external_host:
                        external_host_model = WebinarHost.query.get(
                            external_host['row_id'])
                        if not external_host_model:
                            c_abort(404,
                                    message='Webinar Host id: %s does not'
                                    ' exist' % str(external_host['row_id']))
                        external_hosts, errors = WebinarHostSchema().load(
                            external_host, instance=external_host_model,
                            partial=True)
                        if errors:
                            db.session.rollback()
                            c_abort(422, errors=errors)
                        external_hosts.updated_by = g.current_user['row_id']
                    else:
                        # if external_host row_id not present,
                        # add external_host
                        external_host['webinar_id'] = data.row_id
                        # if same host exists in host_ids so not insert second
                        # time
                        if external_host['host_email'] in host_email_ids:
                            continue
                        # validate and deserialize input
                        external_hosts, errors = \
                            WebinarHostSchema().load(external_host)
                        if errors:
                            c_abort(422, errors=errors)
                        # no errors, so add external_hosts data to db
                        external_hosts.updated_by = g.current_user['row_id']
                        external_hosts.created_by = g.current_user['row_id']
                    if external_hosts:
                        db.session.add(external_hosts)
                db.session.commit()

            # update webinar stats
            update_webinar_stats.s(True, data.row_id).delay()
            # send email when change in rsvps
            rsvp_new_list = []
            for rsvp_new in data.rsvps:
                rsvp_new_list.append(
                    {rsvp_new.email: rsvp_new.contact_person})
            rsvp_changed = rsvp_new_list != rsvp_old_list
            rescheduled = ((old_started_at, old_ended_at)
                           != (data.started_at, data.ended_at))
            # change webinar date in bigmarker
            if not old_is_draft and (rescheduled or rsvp_changed):
                if rescheduled:
                    response = add_update_conference(data)
                    if not response['status']:
                        data.started_at = old_started_at
                        data.ended_at = old_ended_at
                        db.session.add(data)
                        db.session.commit()
                        c_abort(422, message='problem with bigmarker',
                                errors=response['response']['error'])
                # new invitees need not to send email
                send_webinar_update_email.s(
                    True, row_id, new_invitee_emails,
                    invitee_ids, rescheduled).delay()

            # condition for sending emails, if satisfies send emails
            if old_is_draft is True and model.is_draft is False:
                response = add_update_conference(data)
                if not response['status']:
                    data.is_draft = True
                    db.session.add(data)
                    db.session.commit()
                    c_abort(422, message='problem with bigmarker',
                            errors=response['response']['error'])
                if response['conference_id']:
                    pre_registration_user_for_conference(webinar=data)
                    send_webinar_launch_email.s(True, data.row_id).delay()
                    if data.webinar_invitees:
                        add_webinar_invite_notification.s(
                            True, model.row_id, NOTIFY.NT_WEBINAR_INVITED
                        ).delay()
                    # add host
                    if data.webinar_hosts:
                        add_webinar_host_added_notification.s(
                            True, data.row_id, NOTIFY.NT_WEBINAR_HOST_ADDED
                        ).delay()
                    # add participant
                    if data.webinar_participants:
                        add_webinar_participant_added_notification.s(
                            True, data.row_id,
                            NOTIFY.NT_WEBINAR_PARTICIPANT_ADDED).delay()
                    # uncomment this part for rsvp added notification
                    """
                    # add rsvp
                    if data.rsvps:
                        add_webinar_rsvp_added_notification.s(
                            True, data.row_id,
                            NOTIFY.NT_WEBINAR_RSVP_ADDED).delay()
                    """
                    # true specifies mail sending task is in queue
                    data.is_in_process = True
                    db.session.add(data)
                    db.session.commit()
            # if any existing external invitee email changed or
            # new external invitee added then send email to invitee.
            if not old_is_draft and not data.is_draft:
                if new_invitee_emails or invitee_ids:
                    send_webinar_event_new_invitee_email.s(
                        True, data.row_id, new_invitee_emails, invitee_ids
                    ).delay()
                    # true specifies mail sending task is in queue
                    data.is_in_process = True
                    db.session.add(data)
                    db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (host_id)=(25) is not present in table "webinar".
                column = e.orig.diag.message_detail.split('(')[1].split(')')[0]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (webinar_id, participant_email)=(312, tech@gmail.com)
                # already exists.
                column = e.orig.diag.message_detail.split('(')[1].split(')')[0]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
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
        return {'message': 'Updated Webinar id: %s' % str(row_id)}, 200

    @swag_from('swagger_docs/webinar_delete.yml')
    def delete(self, row_id):
        """
        Delete a Webinar
        """
        model = None
        conference_id = None
        try:
            # first find model
            model = Webinar.query.get(row_id)
            if model is None:
                c_abort(404, message='Webinar id: %s does not exist' %
                                     str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            if model.is_draft is False:
                c_abort(422, message='Webinar published,'
                        ' so it cannot be deleted')
            if model.cancelled:
                c_abort(422, message='Webinar cancelled,'
                        ' so it cannot be deleted')
            conference_id = model.conference_id

            if conference_id:
                response = delete_conference(conference_id=conference_id)
                if not response['status']:
                    c_abort(422, message='problem with bigmarker',
                            errors=response['response'])
            db.session.delete(model)
            db.session.commit()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            abort(500)
        return {}, 204

    @swag_from('swagger_docs/webinar_get.yml')
    def get(self, row_id):
        """
        Get a Webinar by id
        """
        model = None
        try:
            # first find model
            model = Webinar.query.filter(Webinar.row_id == row_id).join(
                WebinarInvitee, and_(
                    WebinarInvitee.webinar_id == Webinar.row_id,
                    or_(WebinarInvitee.invitee_id == g.current_user['row_id'],
                        WebinarInvitee.invitee_email ==
                        g.current_user['email'])),
                isouter=True).options(contains_eager(Webinar.invited)).first()
            if model is None:
                c_abort(404, message='Webinar id:'
                        ' %s does not exist' % str(row_id))
            # check ownership
            # for invitee users
            invitee_user_ids = []
            invitee_email_ids = []
            for web in model.webinar_invitees:
                if web.invitee_id:
                    invitee_user_ids.append(web.invitee_id)
                else:
                    invitee_email_ids.append(web.invitee_email)
            # for participant users
            participant_ids = []
            participant_emails = []
            for web in model.webinar_participants:
                if web.participant_id:
                    participant_ids.append(web.participant_id)
                else:
                    participant_emails.append(web.participant_email)
            # for rsvp
            rsvp_emails = [web.email for web in model.rsvps]
            # for host users
            host_ids = []
            host_emails = []
            for web in model.webinar_hosts:
                if web.host_id:
                    host_ids.append(web.host_id)
                else:
                    host_emails.append(web.host_email)

            if (model.created_by != g.current_user['row_id'] and
                    g.current_user['row_id'] not in invitee_user_ids and
                    g.current_user['email'] not in invitee_email_ids and
                    g.current_user['row_id'] not in participant_ids and
                    g.current_user['email'] not in participant_emails and
                    g.current_user['email'] not in rsvp_emails and
                    g.current_user['row_id'] not in host_ids and
                    g.current_user['email'] not in host_emails and
                    not model.open_to_public and (
                    not model.open_to_account_types or
                    g.current_user['account_type'] not in
                    model.open_to_account_types)):
                abort(403)
            # some fields need to be display here so removing
            # from _default_exclude_fields list by making a copy
            local_exclude_list = WebinarSchema._default_exclude_fields[:]
            local_exclude_list_remove = [
                'participants', 'invitees', 'rsvps', 'webinar_hosts',
                'hosts', 'files', 'webinar_participants',
                'external_invitees', 'webinar_invitees']
            # when current user is not admin so remove admin_url
            if g.current_user['account_type'] == ACCOUNT.ACCT_ADMIN:
                local_exclude_list_remove.append('admin_url')

            final_list = list(set(local_exclude_list).difference(
                set(local_exclude_list_remove)))
            include_current_users_groups_only()
            result = WebinarSchema(exclude=final_list).dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class WebinarListAPI(AuthResource):
    """
    Read API for Webinar lists, i.e, more than 1
    """
    model_class = Webinar

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = [
            'invite_logo_url', 'invite_banner_url', 'audio_url', 'video_url',
            'creator', 'host', 'participants', 'rsvps']
        super(WebinarListAPI, self).__init__(*args, **kwargs)

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

        # for union query without current_user filter
        query_filters_union = {}
        query_filters_union['base'] = query_filters['base'][:]
        query_filters_union['filters'] = query_filters['filters'][:]
        # is_draft False filter for participated, invited etc
        query_filters_union['base'].append(
            Webinar.is_draft.is_(False))
        query_for_union = self._build_final_query(
            query_filters_union, query_session, operator)

        query_filters['base'].append(or_(
            Webinar.created_by == g.current_user['row_id'],
            g.current_user['account_type'] == any_(
                Webinar.open_to_account_types),
            Webinar.open_to_public.is_(True)))

        query = self._build_final_query(
            query_filters, query_session, operator)

        join_load = [
            contains_eager(Webinar.invited),
            # invitees and related stuff
            joinedload(Webinar.invitees, innerjoin=innerjoin),
            # participants and related stuff
            joinedload(Webinar.participants, innerjoin=innerjoin),
            # hosts and related stuff
            joinedload(Webinar.hosts, innerjoin=innerjoin)]

        # eager load
        query = query.options(*join_load)

        if not main_filter or main_filter == WEBINAR.MNFT_ALL:
            # for showing webinars current user created,
            # invited, hosted or participated
            if g.current_user['account_type'] == ACCOUNT.ACCT_GUEST:
                invitee_query = query_for_union.join(WebinarInvitee, or_(
                    Webinar.open_to_public.is_(True),
                    and_(
                        (WebinarInvitee.webinar_id == Webinar.row_id),
                        (WebinarInvitee.invitee_email == g.current_user[
                            'email'])))).options(*join_load)
                participant_query = query_for_union.join(
                    WebinarParticipant, or_(
                        Webinar.open_to_public.is_(True),
                        and_(
                            (WebinarParticipant.webinar_id == Webinar.row_id),
                            (WebinarParticipant.participant_email ==
                                g.current_user['email'])))).options(*join_load)
                host_query = query_for_union.join(WebinarHost, or_(
                        Webinar.open_to_public.is_(True),
                        and_(
                            (WebinarHost.webinar_id == Webinar.row_id),
                            (WebinarHost.host_email == g.current_user[
                                'email'])))).options(*join_load)
                final_query = invitee_query.union(participant_query).union(
                    host_query)
            else:
                final_query = query_for_union.join(
                    WebinarInvitee,
                    and_(WebinarInvitee.webinar_id==Webinar.row_id,
                         or_(WebinarInvitee.invitee_id==g.current_user['row_id'],
                             WebinarInvitee.invitee_email==g.current_user['email'])),
                    isouter=True).join(
                    WebinarParticipant,
                    and_(WebinarParticipant.webinar_id==Webinar.row_id,
                         or_(WebinarParticipant.participant_id==g.current_user['row_id'],
                             WebinarParticipant.participant_email==g.current_user['email'])),
                    isouter=True).join(
                    WebinarHost,
                    and_(WebinarHost.webinar_id==Webinar.row_id,
                         or_(WebinarHost.host_id==g.current_user['row_id'],
                             WebinarHost.host_email==g.current_user['email'])),
                    isouter=True).filter(
                    or_(WebinarInvitee.row_id.isnot(None),
                        WebinarParticipant.row_id.isnot(None),
                        WebinarHost.row_id.isnot(None),
                        Webinar.created_by==g.current_user['row_id'],
                        g.current_user['account_type']==any_(
                            Webinar.open_to_account_types),
                        Webinar.open_to_public.is_(True)))
        elif main_filter == WEBINAR.MNFT_INVITED:
            # for showing webinars current user is invited to
            if g.current_user['account_type'] == ACCOUNT.ACCT_GUEST:
                final_query = query_for_union.join(WebinarInvitee, and_(
                    (WebinarInvitee.webinar_id == Webinar.row_id),
                    (WebinarInvitee.invitee_email == g.current_user[
                        'email']))).options(*join_load)
            else:
                final_query = query_for_union.join(WebinarInvitee, and_(
                    (WebinarInvitee.webinar_id == Webinar.row_id),
                    or_(WebinarInvitee.invitee_id == g.current_user[
                        'row_id'], WebinarInvitee.invitee_email ==
                        g.current_user['email']))).options(*join_load)
        elif main_filter == WEBINAR.MNFT_PARTICIPATED:
            # for showing webinars current user is participated
            if g.current_user['account_type'] == ACCOUNT.ACCT_GUEST:
                final_query = query_for_union.join(WebinarParticipant, and_(
                    (WebinarParticipant.webinar_id == Webinar.row_id),
                    (WebinarParticipant.participant_email == g.current_user[
                        'email']))).options(*join_load)
            else:
                final_query = query_for_union.join(WebinarParticipant, and_(
                    (WebinarParticipant.webinar_id == Webinar.row_id),
                    (WebinarParticipant.participant_id == g.current_user[
                        'row_id']))).options(*join_load)
        elif main_filter == WEBINAR.MNFT_HOSTED:
            # for showing webinars current user is hosted
            if g.current_user['account_type'] == ACCOUNT.ACCT_GUEST:
                final_query = query_for_union.join(WebinarHost, and_(
                    (WebinarHost.webinar_id == Webinar.row_id),
                    (WebinarHost.host_email == g.current_user[
                        'email']))).options(*join_load)
            else:
                final_query = query_for_union.join(WebinarHost, and_(
                    (WebinarHost.webinar_id == Webinar.row_id),
                    (WebinarHost.host_id == g.current_user[
                        'row_id']))).options(*join_load)
        elif main_filter == WEBINAR.MNFT_MINE:
            # for showing only webinars created by current user
            query_filters['base'].append(
                Webinar.created_by == g.current_user['row_id'])
            query = self._build_final_query(
                query_filters, query_session, operator)
            final_query = query.options(*join_load)
            # join for webinar invited
            final_query = final_query.join(WebinarInvitee, and_(
                WebinarInvitee.webinar_id == Webinar.row_id, or_(
                    WebinarInvitee.invitee_id == g.current_user['row_id'],
                    WebinarInvitee.invitee_email == g.current_user['email'])),
                isouter=True)

        return final_query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/webinar_get_list.yml')
    def get(self):
        """
        Get the list
        """
        webinar_read_schema = WebinarReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            webinar_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Webinar), operator)
            # making a copy of the main output schema
            webinar_schema = WebinarSchema(
                exclude=WebinarSchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                webinar_schema = WebinarSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching Webinar found')
            result = webinar_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            abort(500)
        return {'results': result.data, 'total': total}, 200


class WebinarCancelledAPI(AuthResource):
    """
    API for maintaing Webinar cancelled feature
    """

    @swag_from('swagger_docs/webinar_cancel_put.yml')
    def put(self, row_id):
        """
        Update a Webinar cancelled
        """
        # first find model
        model = None
        try:
            model = Webinar.query.get(row_id)
            if model is None:
                c_abort(404, message='Webinar id: %s does not exist' %
                        str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            if model.is_draft:
                c_abort(422, message="In draft mode, can't be cancelled")

            if not model.cancelled:
                if model.conference_id:
                    response = delete_conference(data=model)
                    if not response['status']:
                        c_abort(422, message='problem with bigmarker',
                                errors=response['response'])
                model.cancelled = True
                db.session.add(model)
                db.session.commit()
                send_webinar_cancellation_email.s(True, row_id).delay()
                # send webinar cancel notification to invitee
                add_webinar_cancelled_invitee_notification.s(
                    True, row_id, NOTIFY.NT_WEBINAR_CANCELLED).delay()
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Cancelled Webinar id: %s' %
                str(row_id)}, 200


class WebinarConfereceAttendeeAPI(AuthResource):
    """
    To get webinar conference attendee list from third party api
    """

    def put(self, row_id):
        """
        Fetch a Webinar by id
        """
        model = None
        try:
            # first find model
            model = Webinar.query.get(row_id)
            if model is None:
                c_abort(404, message='Webinar id:'
                        ' %s does not exist' % str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            if not model.conference_id:
                c_abort(422, message='Conference id does not exist')
            get_webinar_conference_attendees_list.s(True, row_id).delay()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Fetched Conference Attendee List for '
                'Webinar id: %s' % str(row_id)}, 200


class PublicWebinarAPI(BaseResource):
    """
    CRUD API for managing Webinar publicly
    """

    def get(self, row_id):
        """
        Get a public Webinar by id
        """

        model = None
        try:
            model = Webinar.query.get(row_id)
            if model is None:
                c_abort(404, message='Webinar id: '
                        '%s does not exist' % str(row_id))
            if not model.open_to_public:
                c_abort(403)

            result = PublicWebinarSchema().dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result}, 200


class PublicWebinarListAPI(BaseResource):
    """
    Read API for pubilc Webinar lists, i.e, more than 1
    """

    model_class = Webinar

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = [
            'invite_logo_url', 'invite_banner_url', 'audio_url', 'video_url',
            'creator', 'host', 'participants', 'rsvps']
        super(PublicWebinarListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        query_filters, extra_query, db_projection, s_projection, order, \
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)

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
        query_filters['base'].append(and_(
            Webinar.cancelled.is_(False),
            Webinar.is_draft.is_(False),
            Webinar.open_to_public.is_(True)))

        query = self._build_final_query(query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    def get(self):
        """
        Get the list
        """
        webinar_read_schema = WebinarReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            webinar_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Webinar), operator)
            # making a copy of the main output schema
            webinar_schema = PublicWebinarSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                webinar_schema = PublicWebinarSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching Webinar found')
            result = webinar_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            abort(500)
        return {'results': result.data, 'total': total}, 200


class WebinarReminderAPI(AuthResource):
    """
    api for reminder mail send to all user
    """

    def get(self, row_id):
        """

        :param row_id:
        :return:
        """
        model = None
        try:
            model = Webinar.query.get(row_id)
            if model is None:
                c_abort(404, message='Webinar id: %s does not exist' %
                                     str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            if model.is_draft:
                c_abort(422, message="In draft mode.")

            if model.started_at < dt.utcnow():
                c_abort(422, message='Webinar already started or completed')

            send_webinar_reminder_email.s(True, model.row_id).delay()
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Webinar id: %d Reminder email sent' % row_id}, 200


class ReSendMailToWebinarInvitee(AuthResource):
    """
    Resend mail to all invitee which have not sent when webinar launch
    """
    def put(self, row_id):
        """
        Call task for resend mail for particular event
        :param row_id: id of webinar
        :return:
        """
        # first find model
        model = None
        try:
            model = Webinar.query.get(row_id)
            if model is None:
                c_abort(404, message='Webinar id: %s'
                                     'does not exist' % str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            if model.is_draft:
                c_abort(422, message="In draft mode, can't be launched")
            if model.is_in_process :
                c_abort(422, message="Already processing")
            send_webinar_launch_email.s(True, row_id).delay()

            # true specifies mail sending task is in queue
            model.is_in_process = True
            db.session.add(model)
            db.session.commit()
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Resent mail to Webinar id: %s' %
                           str(row_id)}, 200


class PublishRecordingAPI(AuthResource):
    def put(self, row_id):
        try:
            recording_read_schema = PublishRecordingReadArgSchema(strict=True)
            filters, pfields, sort, pagination, operator = self.parse_args(
                recording_read_schema)
            models = {
                APP.EVNT_WEBINAR : Webinar,
                APP.EVNT_WEBCAST : Webcast}
            model = models[filters['module']].query.get(row_id)
            if not model:
                c_abort(404, message="{} with id {} not found.".format(
                    filters['module'], row_id))
            if model.recording_published:
                c_abort(422, message="recording is already published "
                    "for this {}".format(filters['module']))
            if model.created_by != g.current_user['row_id']:
                abort(403)
            if model.is_draft or not model.conference_id:
                c_abort(422, message="{} not yet launched.".format(
                    filters['module']))
            sub_url = 'conferences/' + model.conference_id + '/recording'
            bigmarkar_response = calling_bigmarker_apis(
                sub_url=sub_url, method='get')
            if not bigmarkar_response.ok:
                message = bigmarkar_response.json().get("message") or ""
                c_abort(422, message=message, errors=bigmarkar_response.json())

            sub_url = 'conferences/' + model.conference_id \
                      + '/publish_recording'
            bigmarkar_response = calling_bigmarker_apis(
                sub_url=sub_url, method='get')
            if not bigmarkar_response.ok:
                message = bigmarkar_response.json().get("message") or ""
                c_abort(422, message=message, errors=bigmarkar_response.json())
            model.recording_published = True
            db.session.add(model)
            db.session.commit()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {"message": "recording published."}, 200