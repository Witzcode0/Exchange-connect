"""
API endpoints for "management profiles" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.expression import case
from flasgger.utils import swag_from

from app import db, c_abort, manageprofilephoto
from app.base.api import AuthResource
from app.auth.decorators import role_permission_required
from app.common.helpers import store_file, delete_files
from app.base import constants as APP
from app.resources.account_profiles.models import AccountProfile
from app.resources.roles import constants as ROLE
from app.resources.management_profiles.models import ManagementProfile
from app.resources.management_profiles.schemas import (
    ManagementProfileSchema, ManagementProfileReadArgsSchema,
    AdminManagementProfileSchema, AdminManagementProfileOrderSchema)
from queueapp.thumbnail_tasks import convert_file_into_thumbnail


# main input and output schema
management_profile_schema = ManagementProfileSchema()
# schema for reading get arguments
management_profile_read_schema = ManagementProfileReadArgsSchema(strict=True)
# admin management profile schema
admin_management_profile_schema = AdminManagementProfileSchema()


class AdminManagementProfileAPI(AuthResource):
    """
    Create, update API for Management Profile
    """
    @role_permission_required(perms=[ROLE.EPT_NU])
    @swag_from('swagger_docs/admin_management_profile_post.yml')
    def post(self):
        """
        Create a management profile
        """
        # get the form data from the request
        account_profile = None
        account_id = None
        json_data = request.form.to_dict()
        if not json_data:
            c_abort(400)
        try:
            # check account_profile exist or not then assign
            # provided account_id to the account_profile_id of table
            if 'account_id' not in json_data or not json_data['account_id']:
                c_abort(422, errors={
                    'account_id': 'Missing data for required field.'})
            if 'account_id' in json_data and json_data['account_id']:
                account_id = json_data.pop('account_id')

            #added manual sequence id to overcome sequence_id not null issue
            json_data['sequence_id'] = 11
            # validate and deserialize input into object
            data, errors = admin_management_profile_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            account_profile = AccountProfile.query.filter(
                AccountProfile.account_id == account_id).first()
            if not account_profile:
                c_abort(404, message='Account id: '
                        '%s does not exist' % str(account_id))
            if account_profile:
                data.account_profile_id = account_profile.row_id
                # fetch the management_profiles associated with the account
                # profile and get the highest in order sequence_id
                last_in_order_profile = ManagementProfile.query.filter_by(
                    account_profile_id=data.account_profile_id).order_by(
                    ManagementProfile.sequence_id.desc()).first()
                if last_in_order_profile:
                    last_in_order_sequence_id =\
                        last_in_order_profile.sequence_id
                    # set the sequence_id as new highest in order sequence_id
                    data.sequence_id = last_in_order_sequence_id + 1
                else:
                    data.sequence_id = 1

            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (account_profile_id, user_id)=(1, 1)
                # already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (account_profile_id)=(999) is not present
                # in table "account_profile"
                column = e.orig.diag.message_detail.split('(')[1].split(')')[0]
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

        fpath = None
        file_data = {'files': {}}
        sub_folder = data.file_subfolder_name()
        profile_photo_full_folder = data.full_folder_path(
            ManagementProfile.root_profile_photo_folder_key)
        if 'profile_photo' in request.files:
            # new file being added
            # add new file
            fpath, fname, ferrors, ftype = store_file(
                manageprofilephoto, request.files['profile_photo'],
                sub_folder=sub_folder, full_folder=profile_photo_full_folder,
                detect_type=True, type_only=True, not_local=True)
            if ferrors:
                db.session.delete(data)
                db.session.commit()
                return ferrors['message'], ferrors['code']
            file_data['files'][fname] = fpath
        # delete files
        if 'profile_photo' in request.form:
            file_data['delete'] = []
            if request.form['profile_photo'] == data.profile_photo:
                file_data['delete'].append(
                    request.form['profile_photo'])
                if file_data['delete']:
                    # delete all mentioned files
                    ferrors = delete_files(
                        file_data['delete'], sub_folder=sub_folder,
                        full_folder=profile_photo_full_folder)
                    if ferrors:
                        return ferrors['message'], ferrors['code']

        try:
            if file_data and (file_data['files'] or 'delete' in file_data):
                # populate db data from file_data
                # parse new files
                if file_data['files']:
                    data.profile_photo = [
                        fname for fname in file_data['files']][0]

            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
            if fpath:
                convert_file_into_thumbnail.s(
                    True, data.row_id, APP.MOD_MGMT_PROFILE,
                    fpath, 'profile').delay()
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

        return {'message': 'Management Profile Added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @role_permission_required(perms=[ROLE.EPT_NU])
    @swag_from('swagger_docs/admin_management_profile_put.yml')
    def put(self, row_id):
        """
        Update a Management Profile
        """
        # first find model
        model = None
        try:
            model = ManagementProfile.query.get(row_id)
            if model is None:
                c_abort(404, message='Management Profile id:'
                        '%s does not exist' % str(row_id))
        except HTTPException as e:
            raise e
        except Exception as e:
            abort(500)

        fpath = None
        file_data = {'files': {}}
        sub_folder = model.file_subfolder_name()
        profile_photo_full_folder = model.full_folder_path(
            ManagementProfile.root_profile_photo_folder_key)
        if 'profile_photo' in request.files:
            # new file being added
            # add new file
            fpath, fname, ferrors, ftype = store_file(
                manageprofilephoto, request.files['profile_photo'],
                sub_folder=sub_folder,
                full_folder=profile_photo_full_folder,
                detect_type=True, type_only=True, not_local=True)
            if ferrors:
                return ferrors['message'], ferrors['code']
            file_data['files'][fname] = fpath
        # delete files
        if 'profile_photo' in request.form:
            file_data['delete'] = []
            if request.form['profile_photo'] == model.profile_photo:
                file_data['delete'].append(
                    request.form['profile_photo'])
                if file_data['delete']:
                    # delete all mentioned files
                    ferrors = delete_files(
                        file_data['delete'], sub_folder=sub_folder,
                        full_folder=profile_photo_full_folder)
                    if ferrors:
                        return ferrors['message'], ferrors['code']
                    if model.profile_thumbnail:
                        th_errors = delete_files(
                            [model.profile_thumbnail], sub_folder=sub_folder,
                            full_folder=profile_photo_full_folder,
                            is_thumbnail=True)
                        if th_errors:
                            return th_errors['message'], th_errors['code']

        try:
            json_data = request.form.to_dict()
            if not json_data and not file_data['files'] and (
                    'delete' not in file_data or not file_data['delete']):
                c_abort(400)
            if 'account_id' in json_data and json_data['account_id']:
                json_data.pop('account_id')
            # validate and deserialize input
            data, errors = management_profile_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so update data to db
            db.session.add(data)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (account_profile_id, user_id)=(1, 1)
                # already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (account_profile_id)=(999) is not present
                # in table "account_profile"
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

        try:
            if file_data and (file_data['files'] or 'delete' in file_data):
                # populate db data from file_data
                # parse new files
                if file_data['files']:
                    data.profile_photo = [
                        fname for fname in file_data['files']][0]

                # any old files to delete
                if 'delete' in file_data:
                    for profile_photo in file_data['delete']:
                        if profile_photo == data.profile_photo:
                            data.profile_photo = None
                            data.profile_thumbnail = None

            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
            if fpath:
                convert_file_into_thumbnail.s(
                    True, data.row_id, APP.MOD_MGMT_PROFILE,
                    fpath, 'profile').delay()
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Updated Management Profile'
                ' id: %s' % str(row_id)}, 200

    @role_permission_required(perms=[ROLE.EPT_NU])
    @swag_from('swagger_docs/admin_management_profile_delete.yml')
    def delete(self, row_id):
        """
        Delete a Management Profile
        """
        model = None
        try:
            # first find model
            model = ManagementProfile.query.get(row_id)
            if model is None:
                c_abort(404, message='Management Profile'
                        ' id: %s does not exist' % str(row_id))
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


class AdminManagementProfileOrderAPI(AuthResource):
    """
    update API for Management Profile oredering
    """

    @role_permission_required(perms=[ROLE.EPT_NU])
    @swag_from('swagger_docs/admin_management_profile_order_put.yml')
    def put(self):
        """
        update the management_profiles's sequence_id
        """
        admin_management_profile_order_schema =\
            AdminManagementProfileOrderSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input
            data, errors =\
                admin_management_profile_order_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            row_ids = data['management_profile_ids']
            count = 1

            # ordering the row_ids according to input for fetching the
            # management_profile in the same order
            ordering = case(
                {row_id: index for index, row_id in enumerate(row_ids)},
                value=ManagementProfile.row_id)
            management_profiles = ManagementProfile.query.filter(
                ManagementProfile.row_id.in_(row_ids)).order_by(
                ordering).all()

            # update the management profile sequence_id for ordering
            for management_profile in management_profiles:
                management_profile.sequence_id = count
                count += 1
                db.session.add(management_profile)
            db.session.commit()

        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Management Profiles Updated'}, 200
