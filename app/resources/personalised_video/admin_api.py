import os
import json
from werkzeug.exceptions import Forbidden, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy import func, and_

from app import db, c_abort, personalisedvideofile, personalisedvideoposterfile, personalisedvideodemofile
from app.auth.decorators import role_permission_required
from app.resources.roles import constants as ROLE
from app.base import constants as APP
from app.base.api import AuthResource
from app.common.helpers import store_file, delete_files, generate_video_email_link,generate_video_token,generate_video_email_token
from app.resources.personalised_video_invitee.schemas import PersonalisedVideoInviteeSchema
from app.resources.personalised_video_invitee.models import PersonalisedVideoInvitee
from app.resources.personalised_video.schemas import PersonalisedVideoSchema, PersonalisedVideoSchemaReadArgsSchema
from app.resources.personalised_video.models import (PersonalisedVideoMaster)
# from queueapp.personalised_video.email_tasks import send_personalised_video_invitee_email
from queueapp.personalised_video_email_tasks import send_video_link_email
from app.resources.accounts.models import Account


class AdminPersonalisedVideoAPI(AuthResource):

    # @role_permission_required(perms=[ROLE.EPT_AA], roles=[ROLE.ERT_SU])
    def post(self):

        """
        create Personalised video
        """
        personalised_video_schema = PersonalisedVideoSchema()
        json_data = request.form.to_dict()
        if 'external_invitees' in json_data:
            json_data['external_invitees'] = json.loads(
                request.form['external_invitees'])

        try:
            invitee_list = []
            data, errors = personalised_video_schema.load(json_data)

            if errors:
                c_abort(422, errors=errors)

            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by

            if data.external_invitees:
                for each_invitee in data.external_invitees:
                    # get token
                    if data.video_type.lower() == APP.VID_TEASER:
                        payload = generate_video_email_token(each_invitee, APP.VID_TEASER)
                        first_half = current_app.config['PERSONALISED_VIDEO_JOIN_ADD_URL']
                        video_url = generate_video_email_link(first_half,
                                                               APP.VID_TEASER, payload=payload)
                    elif data.video_type.lower() == APP.VID_DEMO:
                        payload = generate_video_email_token(each_invitee, APP.VID_DEMO)
                        first_half = current_app.config['PERSONALISED_VIDEO_JOIN_ADD_URL']
                        video_url = generate_video_email_link(first_half,
                                                              APP.VID_DEMO, payload=payload)

                    each_invitee.created_by = g.current_user['row_id']
                    each_invitee.updated_by = g.current_user['row_id']
                    each_invitee.video_url = video_url
                    invitee_list.append(each_invitee.email)

            # for account_id of project
            db.session.add(data)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        video_file_data = {'files': {}, 'types': {}}
        video_baner = {'files': {}}
        sub_folder = data.file_subfolder_name()
        video_teaser_full_folder = data.full_folder_path(
            PersonalisedVideoMaster.root_folder_key)
        video_demo_full_folder = data.full_folder_path(
            PersonalisedVideoMaster.root_video_demo_folder)
        video_baner_full_folder = data.full_folder_path(
            PersonalisedVideoMaster.root_video_poster_folder)

        if 'filename' in request.files:
            #teaser video
            if json_data['video_type'].lower() == APP.VID_TEASER:
                video_path, video_name, ferrors, ftype = store_file(
                    personalisedvideofile, request.files['filename'],
                    sub_folder=sub_folder,
                    full_folder=video_teaser_full_folder, detect_type=True, type_only=True)
                if ferrors:
                    db.session.delete(data)
                    db.session.commit()
                    return ferrors['message'], ferrors['code']
                video_file_data['files'][video_name] = video_path
                video_file_data['types'][video_name] = ftype
            #demo video
            if json_data['video_type'].lower() == APP.VID_DEMO:
                video_path, video_name, ferrors, ftype = store_file(
                    personalisedvideodemofile, request.files['filename'],
                    sub_folder=sub_folder,
                    full_folder=video_demo_full_folder, detect_type=True, type_only=True)
                if ferrors:
                    db.session.delete(data)
                    db.session.commit()
                    return ferrors['message'], ferrors['code']
                video_file_data['files'][video_name] = video_path
                video_file_data['types'][video_name] = ftype

        if 'video_poster_filename' in request.files:
            baner_path, baner_name, ferrors = store_file(
                personalisedvideoposterfile,
                request.files['video_poster_filename'],
                sub_folder=sub_folder, full_folder=video_baner_full_folder)
            if ferrors:
                db.session.delete(data)
                db.session.commit()
                return ferrors['message'], ferrors['code']
            video_baner['files'][baner_name] = baner_path
        else:
            db.session.delete(data)
            db.session.commit()
            c_abort(400, message='No file provided')

        try:
            if video_file_data and (video_file_data['files'] or 'delete' in video_file_data):
                # populate db data from file_data
                # parse new files
                if video_file_data['files']:
                    data.filename = [f for f in video_file_data['files']][0]
                    data.file_type = video_file_data['types'][data.filename]
                    # major file type according to file extension
                    fmtype = (os.path.basename(video_name)).split('.')[-1]
                    if fmtype in APP.VIDEO:
                        data.file_major_type = APP.FILETYP_VD
                    # elif fmtype in AUDIO:
                    #     data.file_major_type = APP.FILETYP_AD
                    # else:
                    #     data.file_major_type = APP.FILETYP_OT
            if video_baner and video_baner['files']:
                if video_baner['files']:
                    data.video_poster_filename = [
                        fname for fname in video_baner['files']][0]

            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()

            if data.external_invitees:
                send_video_link_email.s(True, data.row_id).delay()

        except HTTPException as e:
            db.session.rollback()
            db.session.delete(data)
            db.session.commit()
            raise e
        except Exception as e:
            db.session.rollback()
            db.session.delete(data)
            db.session.commit()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'File Added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    # @role_permission_required(perms=[ROLE.EPT_AA], roles=[ROLE.ERT_SU])
    def put(self, row_id):
        """
        update personlised video file
        """

        personalised_video_schema = PersonalisedVideoSchema()
        model = None
        try:
            model = PersonalisedVideoMaster.query.get(row_id)
            if model is None:
                c_abort(404, message='File id: %s does not exist' %
                                     str(row_id))
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        video_file_data = {'files': {}, 'types': {}}
        video_baner = {'files': {}}
        sub_folder = model.file_subfolder_name()
        video_teaser_full_folder = model.full_folder_path(
            PersonalisedVideoMaster.root_folder_key)
        video_demo_full_folder = model.full_folder_path(
            PersonalisedVideoMaster.root_video_demo_folder)
        video_baner_full_folder = model.full_folder_path(
            PersonalisedVideoMaster.root_video_poster_folder)

        if 'filename' in request.files:
            # new file being added
            # check if there is already a file, then delete it, then add new
            if model.video_type.lower() == APP.VID_TEASER:
                if model.filename:
                    ferrors = delete_files(
                        [model.filename], sub_folder=sub_folder,
                        full_folder=video_teaser_full_folder)
                    if ferrors:
                        return ferrors['message'], ferrors['code']
                # add new file
                fpath, fname, ferrors, ftype = store_file(
                    personalisedvideofile, request.files['filename'],
                    sub_folder=sub_folder,
                    full_folder=video_teaser_full_folder, detect_type=True, type_only=True)
                if ferrors:
                    return ferrors['message'], ferrors['code']
                video_file_data['files'][fname] = fpath
                video_file_data['types'][fname] = ftype
            if model.video_type.lower() == APP.VID_DEMO:
                if model.filename:
                    ferrors = delete_files(
                        [model.filename], sub_folder=sub_folder,
                        full_folder=video_demo_full_folder)
                    if ferrors:
                        return ferrors['message'], ferrors['code']
                # add new file
                fpath, fname, ferrors, ftype = store_file(
                    personalisedvideodemofile, request.files['filename'],
                    sub_folder=sub_folder,
                    full_folder=video_demo_full_folder, detect_type=True, type_only=True)
                if ferrors:
                    return ferrors['message'], ferrors['code']
            video_file_data['files'][fname] = fpath
            video_file_data['types'][fname] = ftype
        if 'video_poster_filename' in request.files:
            poster_path, poster_name, ferrors = store_file(
                personalisedvideoposterfile,
                request.files['video_poster_filename'],
                sub_folder=sub_folder, full_folder=video_baner_full_folder)
            if ferrors:
                return ferrors['message'], ferrors['code']
            video_baner['files'][poster_name] = poster_path

        try:
            json_data = request.form.to_dict()
            print("this is json data :",json_data)
            external_invitees_data = None
            if 'external_invitees' in json_data:
                del json_data['external_invitees']
                external_invitees_data = json.loads(
                    request.form['external_invitees'])

            if not json_data and ('filename' or 'video_poster_filename') not in request.files and not external_invitees_data:
                c_abort(400)

            data = None
            if json_data:
                # validate and deserialize input
                data, errors = personalised_video_schema.load(
                    json_data, instance=model, partial=True)
                if errors:
                    c_abort(422, errors=errors)

            if not data:
                data = model

            if video_file_data and (video_file_data['files'] or 'delete' in video_file_data):
                # populate db data from file_data
                # parse new files
                if video_file_data['files']:
                    data.filename = [f for f in video_file_data['files']][0]
                    data.file_type = video_file_data['types'][data.filename]
            if video_baner and (
                video_baner['files'] or 'delete' in video_baner):
                # parse new files
                if video_baner['files']:
                    data.video_poster_filename = [
                        poster_name for poster_name in video_baner['files']][0]
                if 'delete' in video_baner:
                    for video_baner in video_baner['delete']:
                        if video_baner == data.video_poster_filename:
                            data.video_poster_filename = None


            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()

            # manage video invitees
            invitees_data_model = None
            final_invitee_emails = []
            new_invitee = []
            if external_invitees_data:
                each_invitees = None
                for each_invitee in external_invitees_data:
                    if 'row_id' in each_invitee:
                        each_invitee_model = PersonalisedVideoInvitee.query.get(each_invitee['row_id'])
                        if not each_invitee_model:
                            db.session.rollback()
                            c_abort(404, message='External invitee '
                                                 'id: %s does not exist' %
                                                 str(each_invitee['row_id']
                                                     ))
                        each_invitees, errors = \
                            PersonalisedVideoInviteeSchema().load(
                                each_invitee,
                                instance=each_invitee_model, partial=True)
                        if errors:
                            db.session.rollback()
                            c_abort(422, errors=errors)
                        each_invitees.updated_by = g.current_user[
                            'row_id']
                        #make a list of email id here
                        final_invitee_emails.append(each_invitee['email'])
                    else:

                        #update new invitee addition
                        each_invitee['video_id'] = row_id
                        if data.video_type.lower() == APP.VID_TEASER:
                            payload = generate_video_token(each_invitee, APP.VID_TEASER)
                            # # get email link
                            first_half = current_app.config['PERSONALISED_VIDEO_JOIN_ADD_URL']
                            video_url = generate_video_email_link(first_half,
                                                                  data.video_type.lower(), payload=payload)
                        elif data.video_type.lower() == APP.VID_DEMO:
                            payload = generate_video_token(each_invitee, APP.VID_DEMO)
                            # # get email link
                            first_half = current_app.config['PERSONALISED_VIDEO_JOIN_ADD_URL']
                            video_url = generate_video_email_link(first_half,
                                                                  data.video_type.lower(), payload=payload)

                        each_invitees, errors = PersonalisedVideoInviteeSchema().load(each_invitee)
                        if errors:
                            c_abort(422, errors=errors)
                        # if no errors now add the data
                        each_invitees.created_by = g.current_user['row_id']
                        each_invitees.updated_by = g.current_user['row_id']
                        each_invitees.video_url = video_url
                        final_invitee_emails.append(each_invitee['email'])
                        new_invitee.append(each_invitee['email'])
                    if each_invitees:
                        db.session.add(each_invitees)
                db.session.commit()

                if data.external_invitees:
                    send_video_link_email.s(True, data.row_id).delay()
                print("put api email check!")

        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Updated File id: %s' % str(row_id)}, 200

    def delete(self, row_id):
        """
        Delete a file
        """
        model = None
        try:
            model = PersonalisedVideoMaster.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='File id: %s does not exist' %
                                     str(row_id))
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204

    def get(self, row_id):
        """
        Get a video by id
        """
        personalised_video_schema = PersonalisedVideoSchema()
        model = None
        try:
            model = PersonalisedVideoMaster.query.get(row_id)
            # if model is None or model.deleted:
            if model is None:
                c_abort(404, message='File id: %s does not exist' %
                                     str(row_id))

            # check ownership
            # if model.created_by != g.current_user['row_id']:
            #     abort(403)
            result = personalised_video_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result}, 200


class PersonalisedVideoListAPI(AuthResource):

    model_class = PersonalisedVideoMaster

    def __init__(self, *args, **kwargs):
        super(PersonalisedVideoListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """

        video_type = None
        if 'video_type' in filters and filters['video_type']:
            video_type = filters.pop('video_type')

        account_name = filters.pop('account_name', None)
        query_filters, extra_query, db_projection, s_projection, order, \
        paging = self._build_query(
            filters, pfields, sort, pagination, operator,
            include_deleted=include_deleted)
        # build specific extra queries filters
        if extra_query:
            pass

        if video_type:
            query_filters['base'].append(
                and_(func.lower(PersonalisedVideoMaster.video_type) == video_type.lower()))

        query = self._build_final_query(query_filters, query_session, operator)

        if account_name:
            query = query.filter(func.lower(Account.account_name).like('%' + account_name.lower() + '%'))

        query = query.join(Account, Account.row_id == PersonalisedVideoMaster.account_id)

        return query, db_projection, s_projection, order, paging

    def get(self):

        personalised_video_read_schema = PersonalisedVideoSchemaReadArgsSchema(strict=True)

        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            personalised_video_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(PersonalisedVideoMaster), operator)
            # making a copy of the main output schema
            personalised_video_schema = PersonalisedVideoSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                personalised_video_schema = PersonalisedVideoSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(
                    404, message='No matching reference project types found')
            result = personalised_video_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
