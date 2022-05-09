"""
API endpoints for "webcasts" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g, json
from webargs.flaskparser import parser
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import load_only, joinedload, contains_eager
from sqlalchemy import and_, or_
from flasgger.utils import swag_from

from app import (
    db, c_abort, webcastinvitelogofile, webcastinvitebannerfile)
from app.base.api import AuthResource
from app.base import constants as APP
from app.base.schemas import BaseCommonSchema
from app.common.helpers import (
    store_file, delete_files, verify_event_book_token, add_update_conference,
    delete_conference)
from app.webcast_resources.webcasts.models import Webcast
from app.webcast_resources.webcasts.schemas import (
    WebcastSchema, WebcastReadArgsSchema)
from app.webcast_resources.webcast_rsvps.schemas import WebcastRSVPSchema
from app.webcast_resources.webcasts.helpers import (
    remove_unused_data, remove_participant_or_rsvp_sequence_id,
    check_external_invitee_exists_in_user,
    pre_registration_user_for_conference)
from app.webcast_resources.webcast_participants.models import (
    WebcastParticipant)
from app.webcast_resources.webcast_hosts.models import WebcastHost
from app.webcast_resources.webcast_invitees.models import WebcastInvitee
from app.webcast_resources.webcast_rsvps.models import WebcastRSVP
from app.webcast_resources.webcast_invitees.schemas import (
    WebcastInviteeSchema)
from app.webcast_resources.webcast_hosts.schemas import WebcastHostSchema
from app.webcast_resources.webcast_participants.schemas import (
    WebcastParticipantSchema)
from app.webcast_resources.webcast_stats.models import WebcastStats
from app.resources.notifications import constants as NOTIFY
from app.webcast_resources.webcasts import constants as WEBCAST
from app.resources.accounts import constants as ACCOUNT
from app.resources.users.helpers import include_current_users_groups_only

from queueapp.webcasts.stats_tasks import update_webcast_stats
from queueapp.webcasts.email_tasks import (
    send_webcast_launch_email, send_webcast_update_email,
    send_webcast_cancelled_email, send_webcast_event_new_invitee_email)

from queueapp.webcasts.notification_tasks import (
    add_webcast_invite_notification, add_webcast_host_added_notification,
    add_webcast_participant_added_notification,
    add_webcast_rsvp_added_notification,
    add_webcast_updated_invitee_notification,
    add_webcast_updated_host_notification,
    add_webcast_updated_participant_notification,
    add_webcast_updated_rsvp_notification,
    add_webcast_cancelled_invitee_notification)
from queueapp.webcasts.request_tasks import (
    get_webcast_conference_attendees_list)


class WebcastAPI(AuthResource):
    """
    CRUD API for managing Webcast
    """

    @swag_from('swagger_docs/webcast_post.yml')
    def post(self):
        """
        Create a Webcast
        """
        webcast_schema = WebcastSchema()
        # get the form data from the request
        input_data = None
        input_data = parser.parse(
            BaseCommonSchema(), locations=('querystring',))
        json_data = request.form.to_dict()
        invitee_ids = []
        host_ids = []
        if 'webcast_participants' in json_data:
            json_data['webcast_participants'] = json.loads(request.form[
                'webcast_participants'])
        if 'host_ids' in json_data:
            json_data['host_ids'] = request.form.getlist(
                'host_ids')
        if 'invitee_ids' in json_data:
            json_data['invitee_ids'] = request.form.getlist(
                'invitee_ids')
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
            data, errors = webcast_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.account_id = g.current_user['account_id']
            data.updated_by = data.created_by
            data.stats = WebcastStats()

            if data.webcast_participants:
                for webcast_participant in data.webcast_participants:
                    webcast_participant.created_by = g.current_user['row_id']
                    webcast_participant.updated_by = g.current_user['row_id']
            if data.rsvps:
                for rsvp in data.rsvps:
                    rsvp.created_by = g.current_user['row_id']
                    rsvp.updated_by = g.current_user['row_id']
            if data.external_invitees:
                for external_invitee in data.external_invitees:
                    user_row_id = check_external_invitee_exists_in_user(
                        external_invitee.invitee_email)
                    if user_row_id:
                        external_invitee.user_id = user_row_id
                        external_invitee.invitee_id = user_row_id
                    external_invitee.created_by = g.current_user['row_id']
                    external_invitee.updated_by = g.current_user['row_id']
            if data.external_hosts:
                for external_host in data.external_hosts:
                    external_host.created_by = g.current_user['row_id']
                    external_host.updated_by = g.current_user['row_id']
            if data.external_participants:
                for external_participant in data.external_participants:
                    external_participant.created_by = g.current_user['row_id']
                    external_participant.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()
            # manage files list
            if webcast_schema._cached_files:
                for cf in webcast_schema._cached_files:
                    if cf not in data.files:
                        data.files.append(cf)
            db.session.add(data)
            db.session.commit()
            # manage hosts
            if webcast_schema._cached_host_users:
                host_ids = []
                for host in webcast_schema._cached_host_users:
                    if host not in data.hosts:
                        db.session.add(WebcastHost(
                            webcast_id=data.row_id,
                            host_id=host.row_id,
                            created_by=data.created_by,
                            updated_by=data.created_by))
                        host_ids.append(host.row_id)
                db.session.commit()
            # manage invitees
            if webcast_schema._cached_contact_users:
                for invitee in webcast_schema._cached_contact_users:
                    if invitee not in data.invitees:
                        db.session.add(WebcastInvitee(
                            webcast_id=data.row_id,
                            invitee_id=invitee.row_id,
                            user_id=invitee.row_id,
                            created_by=data.created_by,
                            updated_by=data.created_by))
                        invitee_ids.append(invitee.row_id)
                db.session.commit()
            # update webcast stats
            update_webcast_stats.s(True, data.row_id).delay()

        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (webcast_id, participant_email)=(193, tes@gmail.com)
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
            Webcast.root_invite_logo_folder)
        invite_banner_full_folder = data.full_folder_path(
            Webcast.root_invite_banner_folder)
        # #TODO: audio video used in future

        if 'invite_logo_filename' in request.files:
            logo_path, logo_name, ferrors = store_file(
                webcastinvitelogofile, request.files['invite_logo_filename'],
                sub_folder=sub_folder, full_folder=invite_logo_full_folder)
            if ferrors:
                db.session.delete(data)
                db.session.commit()
                return ferrors['message'], ferrors['code']
            invite_logo['files'][logo_name] = logo_path
        if 'invite_banner_filename' in request.files:
            banner_path, banner_name, ferrors = store_file(
                webcastinvitebannerfile,
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

            # launched emails are sending from here
            # and condition to send notification to invitees
            if data.is_draft is False:
                response = add_update_conference(data)
                if not response['status']:
                    db.session.delete(data)
                    db.session.commit()
                    c_abort(422, message='problem with bigmarker',
                            errors=response['response'].get('error', {}))
                if response['conference_id']:
                    pre_registration_user_for_conference(webcast=data)
                    send_webcast_launch_email.s(True, data.row_id).delay()
                    if data.webcast_invitees or data.external_invitees:
                        add_webcast_invite_notification.s(
                            True, data.row_id, NOTIFY.NT_WEBCAST_INVITED
                        ).delay()
                    # add host
                    if data.webcast_hosts or data.external_hosts:
                        add_webcast_host_added_notification.s(
                            True, data.row_id, NOTIFY.NT_WEBCAST_HOST_ADDED
                        ).delay()
                    # add participant
                    if data.webcast_participants or data.external_participants:
                        add_webcast_participant_added_notification.s(
                            True, data.row_id,
                            NOTIFY.NT_WEBCAST_PARTICIPANT_ADDED).delay()

                    # true specifies mail sending task is in queue
                    data.is_in_process = True
                    db.session.add(data)
                    db.session.commit()
                    # uncomment this part for rsvp added notification
                    """
                    # add rsvp
                    if data.rsvps:
                        add_webcast_rsvp_added_notification.s(
                            True, data.row_id,
                            NOTIFY.NT_WEBCAST_RSVP_ADDED).delay()
                    """
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            db.session.delete(data)
            db.session.commit()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Webcast added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @swag_from('swagger_docs/webcast_put.yml')
    def put(self, row_id):
        """
        Update a Webcast
        """
        webcast_schema = WebcastSchema()
        # first find model
        model = None
        invitee_ids = []
        host_ids = []
        try:
            # get the form data from the request
            input_data = None
            input_data = parser.parse(
                BaseCommonSchema(), locations=('querystring',))
            model = Webcast.query.get(row_id)
            if model is None:
                c_abort(404, message='Webcast id:'
                        '%s does not exist' % str(row_id))
            # is_draft status, to be used for sending email for webcast launch
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
            Webcast.root_invite_logo_folder)
        invite_banner_full_folder = model.full_folder_path(
            Webcast.root_invite_banner_folder)

        if 'invite_logo_filename' in request.files:
            logo_path, logo_name, ferrors = store_file(
                webcastinvitelogofile, request.files['invite_logo_filename'],
                sub_folder=sub_folder, full_folder=invite_logo_full_folder)
            if ferrors:
                return ferrors['message'], ferrors['code']
            invite_logo['files'][logo_name] = logo_path
        if 'invite_banner_filename' in request.files:
            banner_path, banner_name, ferrors = store_file(
                webcastinvitebannerfile,
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
            webcast_participant_data = None
            if 'webcast_participants' in json_data:
                del json_data['webcast_participants']
                webcast_participant_data = json.loads(
                    request.form['webcast_participants'])
            if 'host_ids' in json_data:
                json_data['host_ids'] = request.form.getlist('host_ids')
            if 'invitee_ids' in json_data:
                json_data['invitee_ids'] = request.form.getlist('invitee_ids')
            if 'file_ids' in json_data:
                json_data['file_ids'] = request.form.getlist('file_ids')

            rsvp_data = None  # for rsvp data
            if 'rsvps' in json_data:
                del json_data['rsvps']
                rsvp_data = json.loads(request.form['rsvps'])

            external_invitee_data = None  # for external invitee data
            if 'external_invitees' in json_data:
                del json_data['external_invitees']
                external_invitee_data = json.loads(request.form[
                    'external_invitees'])
            external_host_data = None  # for external host data
            if 'external_hosts' in json_data:
                del json_data['external_hosts']
                external_host_data = json.loads(request.form[
                    'external_hosts'])
            external_participant_data = None  # for external participant data
            if 'external_participants' in json_data:
                del json_data['external_participants']
                external_participant_data = json.loads(request.form[
                    'external_participants'])
            if 'cc_emails' in json_data:
                del json_data['cc_emails']
                json_data['cc_emails'] = request.form.getlist('cc_emails')

            if (not json_data and  # <- no text data
                    not invite_logo['files'] and  # no invite_logo upload
                    not invite_banner['files'] and (  # no invite_banner upload
                    'delete' not in invite_logo or  # no invite_logo delete
                    not invite_logo['delete']) and (
                    'delete' not in invite_banner or  # no invite_banner delete
                    not invite_banner['delete']) and
                    not webcast_participant_data and not rsvp_data and
                    not external_participant_data and
                    not external_host_data and not external_invitee_data):
                # no data of any sort
                c_abort(400)
            # validate and deserialize input
            data = None
            if json_data:
                data, errors = webcast_schema.load(
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
            if webcast_schema._cached_files or 'file_ids' in json_data:
                # add new ones
                for cf in webcast_schema._cached_files:
                    if cf not in data.files:
                        data.files.append(cf)
                # remove old ones
                for oldcf in data.files[:]:
                    if oldcf not in webcast_schema._cached_files:
                        data.files.remove(oldcf)
                db.session.add(data)
                db.session.commit()
            # manage hosts
            if webcast_schema._cached_host_users or 'host_ids' in json_data:
                host_ids = []
                for host in webcast_schema._cached_host_users:
                    if host not in data.hosts:
                        host_ids.append(host.row_id)
                        db.session.add(WebcastHost(
                            webcast_id=data.row_id,
                            host_id=host.row_id,
                            created_by=g.current_user['row_id'],
                            updated_by=g.current_user['row_id']))
                # remove old ones
                for oldhost in data.webcast_hosts[:]:
                    if (oldhost.host not in webcast_schema._cached_host_users):
                        if oldhost in data.webcast_hosts:
                            if oldhost.host_id:
                                db.session.delete(oldhost)
                                db.session.commit()
                db.session.commit()
            # manage invitees
            final_invitee_email_ids =[]
            if (webcast_schema._cached_contact_users or
                    'invitee_ids' in json_data):
                for invitee in webcast_schema._cached_contact_users:
                    final_invitee_email_ids.append(invitee.email)
                    if invitee not in data.invitees:
                        invitee_ids.append(invitee.row_id)
                        db.session.add(WebcastInvitee(
                            webcast_id=data.row_id,
                            invitee_id=invitee.row_id,
                            user_id=invitee.row_id,
                            created_by=g.current_user['row_id'],
                            updated_by=g.current_user['row_id']))
                # remove old ones
                for oldinvite in data.webcast_invitees[:]:
                    if (oldinvite.invitee not in
                            webcast_schema._cached_contact_users):
                        if oldinvite in data.webcast_invitees:
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
                        rsvp_model = WebcastRSVP.query.get(rsvp['row_id'])
                        if not rsvp_model:
                            c_abort(404, message='Webcast '
                                                 'RSVP id: %s does not exist' %
                                                 str(rsvp['row_id']))
                        rsvps, errors = WebcastRSVPSchema().load(
                            rsvp, instance=rsvp_model, partial=True)
                        if errors:
                            db.session.rollback()
                            c_abort(422, errors=errors)
                        rsvps.updated_by = g.current_user['row_id']
                    else:
                        # if rsvp row_id not present, add rsvp
                        rsvp['webcast_id'] = data.row_id
                        # validate and deserialize input
                        rsvps, errors = WebcastRSVPSchema().load(rsvp)
                        if errors:
                            c_abort(422, errors=errors)
                        # no errors, so add rsvps data to db
                        rsvps.updated_by = g.current_user['row_id']
                        rsvps.created_by = g.current_user['row_id']
                    if rsvps:
                        db.session.add(rsvps)
                db.session.commit()
            # manage webcast_invitees
            external_invitee_model = None
            new_invitee_emails = []
            if external_invitee_data:
                for external_invitee in external_invitee_data:
                    external_invitees = None
                    # if webcast_invitee found, update the webcast_invitee
                    if 'row_id' in external_invitee:
                        external_invitee_model = WebcastInvitee.query.get(
                            external_invitee['row_id'])
                        if not external_invitee_model:
                            db.session.rollback()
                            c_abort(404, message='External invitee '
                                                 'id: %s does not exist' %
                                                 str(external_invitee['row_id']
                                                     ))
                        external_invitees, errors = \
                            WebcastInviteeSchema().load(
                                external_invitee,
                                instance=external_invitee_model, partial=True)
                        if errors:
                            db.session.rollback()
                            c_abort(422, errors=errors)
                        external_invitees.updated_by = g.current_user[
                            'row_id']
                        final_invitee_email_ids.append(
                            external_invitees.invitee_email)
                    else:
                        # if external_invitee row_id not present,
                        # add external_invitee
                        external_invitee['webcast_id'] = data.row_id
                        # validate and deserialize input
                        external_invitees, errors = (
                            WebcastInviteeSchema().load(external_invitee))
                        if errors:
                            c_abort(422, errors=errors)
                        user_row_id = check_external_invitee_exists_in_user(
                            external_invitees.invitee_email)
                        if user_row_id:
                            external_invitees.user_id = user_row_id
                            external_invitee.invitee_id = user_row_id
                        # no errors, so add external_invitees data to db
                        external_invitees.updated_by = g.current_user['row_id']
                        external_invitees.created_by = g.current_user['row_id']
                        final_invitee_email_ids.append(
                            external_invitees.invitee_email)
                        new_invitee_emails.append(
                            external_invitee.invitee_email)
                    if external_invitees:
                        db.session.add(external_invitees)
                db.session.commit()

            if external_invitee_data is not None:
                WebcastInvitee.query.filter(and_(
                    WebcastInvitee.webcast_id == data.row_id,
                    WebcastInvitee.invitee_email.notin_(
                        final_invitee_email_ids))).delete(
                    synchronize_session=False)
                db.session.commit()

            # manage webcast_hosts
            external_host_model = None
            if external_host_data:
                for external_host in external_host_data:
                    external_hosts = None
                    # if webcast_invitee found, update the webcast_host
                    if 'row_id' in external_host:
                        external_host_model = WebcastHost.query.get(
                            external_host['row_id'])
                        if not external_host_model:
                            c_abort(404, message='External host '
                                                 'id: %s does not exist' %
                                                 str(external_host['row_id']
                                                     ))
                        external_hosts, errors = WebcastHostSchema().load(
                            external_host, instance=external_host_model,
                            partial=True)
                        if errors:
                            db.session.rollback()
                            c_abort(422, errors=errors)
                        external_hosts.updated_by = g.current_user['row_id']
                    else:
                        # if external_host row_id not present,
                        # add external_host
                        external_host['webcast_id'] = data.row_id
                        # validate and deserialize input
                        external_hosts, errors = (
                            WebcastHostSchema().load(external_host))
                        if errors:
                            c_abort(422, errors=errors)
                        # no errors, so add external_hosts data to db
                        external_hosts.updated_by = g.current_user['row_id']
                        external_hosts.created_by = g.current_user['row_id']
                    if external_hosts:
                        db.session.add(external_hosts)
                db.session.commit()
            # when webcast_participant_data or external_participant_data
            # remove participant sequence ids for update
            if webcast_participant_data or external_participant_data:
                remove_participant_or_rsvp_sequence_id(
                    webcast_participant_data=webcast_participant_data,
                    external_participant_data=external_participant_data)
            # if webcast_participant_data and external_participant_data and
            # same participant user exists in both object so remove from
            # external_participant_data
            if webcast_participant_data and external_participant_data:
                unused, external_participant_data = remove_unused_data(
                    webcast_participant_data=webcast_participant_data,
                    external_participant_data=external_participant_data)
            # manage participants
            if webcast_participant_data:
                for webcast_pcpt in webcast_participant_data:
                    webcast_participant = None
                    # if webcast_participant found,
                    # update the webcast_participant
                    if 'row_id' in webcast_pcpt:
                        webcast_pcpt_model = \
                            WebcastParticipant.query.get(
                                webcast_pcpt['row_id'])
                        if not webcast_pcpt_model:
                            c_abort(404, message='External participant '
                                                 'id: %s does not exist' %
                                                 str(webcast_pcpt['row_id']))
                        webcast_participant, errors = \
                            WebcastParticipantSchema().load(
                                webcast_pcpt, instance=webcast_pcpt_model,
                                partial=True)
                        if errors:
                            db.session.rollback()
                            c_abort(422, errors=errors)
                        webcast_participant.updated_by = g.current_user[
                            'row_id']
                    else:
                        # if webcast_participant row_id not present,
                        # add participant
                        webcast_pcpt['webcast_id'] = data.row_id
                        # validate and deserialize input
                        webcast_participant, errors = (
                            WebcastParticipantSchema().load(webcast_pcpt))
                        if errors:
                            c_abort(422, errors=errors)
                        # no errors, so add participants data to db
                        webcast_participant.updated_by = g.current_user[
                            'row_id']
                        webcast_participant.created_by = g.current_user[
                            'row_id']
                    if webcast_participant:
                        db.session.add(webcast_participant)
                db.session.commit()
            # manage webcast_participants
            external_participant_model = None
            if external_participant_data:
                for external_participant in external_participant_data:
                    external_participants = None
                    # if webcast_participant found,
                    # update the webcast_participant
                    if 'row_id' in external_participant:
                        external_participant_model = \
                            WebcastParticipant.query.get(
                                external_participant['row_id'])
                        if not external_participant_model:
                            c_abort(404, message='External participant '
                                                 'id: %s does not exist' %
                                                 str(external_participant[
                                                     'row_id']))
                        external_participants, errors = \
                            WebcastParticipantSchema().load(
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
                        external_participant['webcast_id'] = data.row_id
                        # validate and deserialize input
                        external_participants, errors = (
                            WebcastParticipantSchema().load(
                                external_participant))
                        if errors:
                            c_abort(422, errors=errors)
                        # no errors, so add external_participants data to db
                        external_participants.updated_by = \
                            g.current_user['row_id']
                        external_participants.created_by = \
                            g.current_user['row_id']
                    if external_participants:
                        db.session.add(external_participants)
                db.session.commit()
            # update webcast stats
            update_webcast_stats.s(True, data.row_id).delay()
            # webcast sending emails when change in rsvps
            rsvp_new_list = []
            for rsvp_new in data.rsvps:
                rsvp_new_list.append(
                    {rsvp_new.email: rsvp_new.contact_person})
            if (model.is_draft is False and (
                    rsvp_new_list != rsvp_old_list
                    or old_started_at, old_ended_at !=
                                       data.started_at, data.ended_at)):
                send_webcast_update_email.s(
                    True, data.row_id, new_invitee_emails, invitee_ids).delay()
                # #TODO: used in future
                """
                # webcast update invitee notification
                add_webcast_updated_invitee_notification.s(
                    True, data.row_id,
                    NOTIFY.NT_WEBCAST_UPDATED_INVITEE).delay()
                # webcast update host notification
                add_webcast_updated_host_notification.s(
                    True, data.row_id,
                    NOTIFY.NT_WEBCAST_UPDATED_HOST).delay()
                # webcast update rsvp notification
                add_webcast_updated_rsvp_notification.s(
                    True, data.row_id,
                    NOTIFY.NT_WEBCAST_UPDATED_RSVP).delay()
                # webcast update participant notification
                add_webcast_updated_participant_notification.s(
                    True, data.row_id,
                    NOTIFY.NT_WEBCAST_UPDATED_PARTICIPANT).delay()
                """

            # condition for sending emails, if satisfies send emails
            # and condition to send notification to invitees
            if old_is_draft is True and model.is_draft is False:
                response = add_update_conference(data)
                if not response['status']:
                    data.is_draft = True
                    db.session.add(data)
                    db.session.commit()
                    c_abort(422, message='problem with bigmarker',
                            errors=response['response']['error'])
                if response['conference_id']:
                    pre_registration_user_for_conference(webcast=data)
                    send_webcast_launch_email.s(True, data.row_id).delay()
                    if data.webcast_invitees:
                        add_webcast_invite_notification.s(
                            True, model.row_id, NOTIFY.NT_WEBCAST_INVITED
                        ).delay()
                    # add host
                    if data.webcast_hosts:
                        add_webcast_host_added_notification.s(
                            True, data.row_id, NOTIFY.NT_WEBCAST_HOST_ADDED
                        ).delay()
                    # add participant
                    if data.webcast_participants:
                        add_webcast_participant_added_notification.s(
                            True, data.row_id, NOTIFY.NT_WEBCAST_PARTICIPANT_ADDED
                        ).delay()

                    # true specifies mail sending task is in queue
                    data.is_in_process = True
                    db.session.add(data)
                    db.session.commit()
                    # uncomment this part for rsvp added notification
                    """
                    # add rsvp
                    if data.rsvps:
                        add_webcast_rsvp_added_notification.s(
                            True, data.row_id,
                            NOTIFY.NT_WEBCAST_RSVP_ADDED).delay()
                    """

            if not old_is_draft and not data.is_draft:
                if new_invitee_emails or invitee_ids:
                    send_webcast_event_new_invitee_email.s(
                        True, data.row_id, new_invitee_emails, invitee_ids
                    ).delay()
                    # true specifies mail sending task is in queue
                    data.is_in_process = True
                    db.session.add(data)
                    db.session.commit()
        except IntegrityError as e:
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (host_id)=(25) is not present in table "webcast".
                column = e.orig.diag.message_detail.split('(')[1].split(')')[0]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (webcast_id, participant_email)=(84, s@gmail.com)
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
        return {'message': 'Updated Webcast id: %s' % str(row_id)}, 200

    @swag_from('swagger_docs/webcast_delete.yml')
    def delete(self, row_id):
        """
        Delete a Webcast
        """
        model = None
        conference_id = None
        try:
            # first find model
            model = Webcast.query.get(row_id)
            if model is None:
                c_abort(404, message='Webcast id: %s does not exist' %
                                     str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            if model.is_draft is False:
                c_abort(422, message='Webcast published,'
                        ' so it cannot be deleted')
            if model.cancelled:
                c_abort(422, message='Webcast cancelled,'
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

    @swag_from('swagger_docs/webcast_get.yml')
    def get(self, row_id):
        """
        Get a Webcast by id
        """
        model = None
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
                input_data['token'], APP.EVNT_WEBCAST)
            if event_data:
                # if current user is guest user
                web_invitee = WebcastInvitee.query.filter(
                    and_(
                        WebcastInvitee.webcast_id == event_data['event_id'],
                        WebcastInvitee.row_id == event_data['invite_id'],
                        WebcastInvitee.user_id.is_(None))).first()
                if web_invitee:
                    web_invitee.user_id = g.current_user['row_id']
                    db.session.add(web_invitee)
                    db.session.commit()
            else:
                c_abort(422, message='Token invalid', errors={
                    'token': ['Token invalid']})
        try:
            # first find model
            model = Webcast.query.filter(Webcast.row_id == row_id).join(
                WebcastInvitee, and_(
                    WebcastInvitee.webcast_id == Webcast.row_id,
                    WebcastInvitee.user_id == g.current_user['row_id']),
                isouter=True).options(contains_eager(Webcast.invited)).first()
            if model is None:
                c_abort(404, message='Webcast id:'
                        ' %s does not exist' % str(row_id))
            # check ownership
            invitee_user_ids = [evnt.user_id for evnt in
                                model.webcast_invitees]
            participant_ids = [evnt.participant_id for evnt in
                               model.webcast_participants]
            participant_emails = [evnt.participant_email for evnt in
                                  model.webcast_participants]
            rsvp_emails = [evnt.email for evnt in model.rsvps]
            host_ids = [evnt.host_id for evnt in
                        model.webcast_hosts]
            host_emails = [evnt.host_email for evnt in
                           model.webcast_hosts]
            # if model is there, if current user is not event creator and
            # not collaborator and not host and not participant and not rsvp
            # current user can not book particular event, so 403 error arise
            if (model.created_by != g.current_user['row_id'] and
                    g.current_user['row_id'] not in invitee_user_ids and
                    g.current_user['row_id'] not in participant_ids and
                    g.current_user['email'] not in participant_emails and
                    g.current_user['email'] not in rsvp_emails and
                    g.current_user['row_id'] not in host_ids and
                    g.current_user['email'] not in host_emails):
                c_abort(403)
            # some fields need to be display here so removing
            # from _default_exclude_fields list by making a copy
            local_exclude_list = WebcastSchema._default_exclude_fields[:]
            local_exclude_list_remove = [
                'external_hosts', 'external_invitees', 'webcast_participants',
                'hosts', 'webcast_invitees', 'files', 'invitees',
                'rsvps', 'participants']
            final_list = list(set(local_exclude_list).difference(
                set(local_exclude_list_remove)))
            include_current_users_groups_only()
            result = WebcastSchema(exclude=final_list).dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class WebcastListAPI(AuthResource):
    """
    Read API for Webcast lists, i.e, more than 1
    """
    model_class = Webcast

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = [
            'invite_logo_url', 'invite_banner_url', 'audio_url', 'video_url',
            'creator', 'hosts', 'participants']
        super(WebcastListAPI, self).__init__(*args, **kwargs)

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
            Webcast.is_draft.is_(False))
        query_for_union = self._build_final_query(
            query_filters_union, query_session, operator)

        # for normal query
        query_filters['base'].append(
            Webcast.created_by == g.current_user['row_id'])

        query = self._build_final_query(query_filters, query_session, operator)

        join_load = [
            contains_eager(Webcast.invited),
            # invitees and related stuff
            joinedload(Webcast.invitees, innerjoin=innerjoin),
            # participants and related stuff
            joinedload(Webcast.participants, innerjoin=innerjoin),
            # hosts and related stuff
            joinedload(Webcast.hosts, innerjoin=innerjoin)]

        # eager load
        query = query.options(*join_load)

        if not main_filter or main_filter == WEBCAST.MNFT_ALL:
            # for showing webcasts current user created,
            # invited, hosted or participated
            if g.current_user['account_type'] == ACCOUNT.ACCT_GUEST:
                invitee_query = query_for_union.join(WebcastInvitee, and_(
                    (WebcastInvitee.webcast_id == Webcast.row_id),
                    (WebcastInvitee.user_id == g.current_user[
                        'row_id']))).options(*join_load)
                participant_query = query_for_union.join(
                    WebcastParticipant, and_(
                        (WebcastParticipant.webcast_id == Webcast.row_id),
                        (WebcastParticipant.participant_email ==
                            g.current_user['email']))).options(*join_load)
                host_query = query_for_union.join(WebcastHost, and_(
                    (WebcastHost.webcast_id == Webcast.row_id),
                    (WebcastHost.host_email == g.current_user[
                        'email']))).options(*join_load)
                final_query = invitee_query.union(participant_query).union(
                    host_query)

                # join for contains eager
                final_query = final_query.join(WebcastInvitee, and_(
                    WebcastInvitee.webcast_id == Webcast.row_id,
                    WebcastInvitee.user_id == g.current_user['row_id']),
                                               isouter=True)
            else:
                final_query = query_for_union.join(
                    WebcastInvitee,
                    and_(WebcastInvitee.webcast_id==Webcast.row_id,
                         or_(WebcastInvitee.invitee_id==g.current_user['row_id'],
                             WebcastInvitee.invitee_email==g.current_user['email'])),
                    isouter=True).join(
                    WebcastParticipant, and_(
                        WebcastParticipant.webcast_id==Webcast.row_id,
                        or_(WebcastParticipant.participant_id==g.current_user['row_id']),
                            WebcastParticipant.participant_email==g.current_user['email']),
                    isouter=True).join(
                    WebcastHost,
                    and_(WebcastHost.webcast_id==Webcast.row_id,
                         or_(WebcastHost.host_id==g.current_user['row_id'],
                             WebcastHost.host_email==g.current_user['email'])),
                    isouter=True).filter(
                    or_(WebcastInvitee.row_id.isnot(None),
                        WebcastParticipant.row_id.isnot(None),
                        WebcastHost.row_id.isnot(None),
                        Webcast.created_by==g.current_user['row_id']))

        elif main_filter == WEBCAST.MNFT_INVITED:
            # for showing webcasts current user is invited to
            if g.current_user['account_type'] == ACCOUNT.ACCT_GUEST:
                final_query = query_for_union.join(WebcastInvitee, and_(
                    (WebcastInvitee.webcast_id == Webcast.row_id),
                    (WebcastInvitee.invitee_email == g.current_user[
                        'email']))).options(*join_load)
            else:
                final_query = query_for_union.join(WebcastInvitee, and_(
                    (WebcastInvitee.webcast_id == Webcast.row_id),
                    (WebcastInvitee.invitee_id == g.current_user[
                        'row_id']))).options(*join_load)
        elif main_filter == WEBCAST.MNFT_PARTICIPATED:
            # for showing webcasts current user is participated
            if g.current_user['account_type'] == ACCOUNT.ACCT_GUEST:
                final_query = query_for_union.join(WebcastParticipant, and_(
                    (WebcastParticipant.webcast_id == Webcast.row_id),
                    (WebcastParticipant.participant_email == g.current_user[
                        'email']))).options(*join_load)
            else:
                final_query = query_for_union.join(WebcastParticipant, and_(
                    (WebcastParticipant.webcast_id == Webcast.row_id),
                    (WebcastParticipant.participant_id == g.current_user[
                        'row_id']))).options(*join_load)
        elif main_filter == WEBCAST.MNFT_HOSTED:
            # for showing webcasts current user is hosted
            if g.current_user['account_type'] == ACCOUNT.ACCT_GUEST:
                final_query = query_for_union.join(WebcastHost, and_(
                    (WebcastHost.webcast_id == Webcast.row_id),
                    (WebcastHost.host_email == g.current_user[
                        'email']))).options(*join_load)
            else:
                final_query = query_for_union.join(WebcastHost, and_(
                    (WebcastHost.webcast_id == Webcast.row_id),
                    (WebcastHost.host_id == g.current_user[
                        'row_id']))).options(*join_load)
        elif main_filter == WEBCAST.MNFT_MINE:
            # for showing only webcasts created by current user
            query_filters['base'].append(
                Webcast.created_by == g.current_user['row_id'])
            query = self._build_final_query(
                query_filters, query_session, operator)
            final_query = query.options(*join_load)
            # join for webcast invited
            final_query = final_query.join(WebcastInvitee, and_(
                WebcastInvitee.webcast_id == Webcast.row_id, or_(
                    WebcastInvitee.invitee_id == g.current_user['row_id'],
                    WebcastInvitee.invitee_email == g.current_user['email'])),
                isouter=True)

        return final_query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/webcast_get_list.yml')
    def get(self):
        """
        Get the list
        """
        webcast_read_schema = WebcastReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            webcast_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Webcast), operator)
            # making a copy of the main output schema
            webcast_schema = WebcastSchema(
                exclude=WebcastSchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                webcast_schema = WebcastSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching Webcast found')
            result = webcast_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            abort(500)
        return {'results': result.data, 'total': total}, 200


class WebcastCancelledAPI(AuthResource):
    """
    API for maintaing Webcast cancelled feature
    """

    @swag_from('swagger_docs/webcast_cancel_put.yml')
    def put(self, row_id):
        """
        Update a webcast cancelled
        """
        # first find model
        model = None
        try:
            model = Webcast.query.get(row_id)
            if model is None:
                c_abort(404, message='Webcast id: %s does not exist' %
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
                send_webcast_cancelled_email.s(True, row_id).delay()
                # send webcast cancel notification to invitee
                add_webcast_cancelled_invitee_notification.s(
                    True, row_id, NOTIFY.NT_WEBCAST_CANCELLED).delay()
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Cancelled Webcast id: %s' %
                str(row_id)}, 200


class WebcastConfereceAttendeeAPI(AuthResource):
    """
    To get webcast conference attendee list from third party api
    """

    def put(self, row_id):
        """
        Fetch a Webcast by id
        """
        model = None
        try:
            # first find model
            model = Webcast.query.get(row_id)
            if model is None:
                c_abort(404, message='Webcast id:'
                        ' %s does not exist' % str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            if not model.conference_id:
                c_abort(422, message='Conference id does not exist')
            get_webcast_conference_attendees_list.s(True, row_id).delay()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Fetched Conference Attendee List for '
                'Webcast id: %s' % str(row_id)}, 200

class ReSendMailToWebcastInvitee(AuthResource):
    """
    Resend mail to all invitee which have not sent when Webcast launch
    """
    def put(self, row_id):
        """
        Call task for resend mail for particular webcast
        :param row_id: id of webcast
        :return:
        """
        # first find model
        model = None
        try:
            model = Webcast.query.get(row_id)
            if model is None:
                c_abort(404, message='Webcast id: %s'
                                     'does not exist' % str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            if model.is_draft:
                c_abort(422, message="In draft mode, can't be launched")
            if model.is_in_process :
                c_abort(422, message="Already processing")
            send_webcast_launch_email.s(True, row_id).delay()

            # true specifies mail sending task is in queue
            model.is_in_process = True
            db.session.add(model)
            db.session.commit()
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Resent mail to Webcast id: %s' %
                           str(row_id)}, 200