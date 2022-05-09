"""
API endpoints for "management profiles" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.expression import case
from sqlalchemy.orm import load_only, joinedload
from flasgger.utils import swag_from

from app import db, c_abort, manageprofilephoto
from app.base.api import AuthResource
from app.common.helpers import store_file, delete_files
from app.base import constants as APP
from app.resources.management_profiles.models import ManagementProfile
from app.resources.management_profiles.schemas import (
    ManagementProfileSchema, ManagementProfileReadArgsSchema,
    ManagementProfileOrderSchema)
from queueapp.thumbnail_tasks import convert_file_into_thumbnail


class ManagementProfileAPI(AuthResource):
    """
    Create, update, delete API for Management Profile
    """

    @swag_from('swagger_docs/management_profile_post.yml')
    def post(self):
        """
        Create a management profile
        """
        management_profile_schema = ManagementProfileSchema()
        # get the form data from the request
        json_data = request.form
        if not json_data:
            c_abort(400)
        try:
            # validate and deserialize input into object
            data, errors = management_profile_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.account_profile_id = g.current_user['account_profile_id']
            # fetch the management_profiles associated with the account
            # profile and get the highest in order sequence_id
            last_in_order_profile = ManagementProfile.query.filter_by(
                account_profile_id=data.account_profile_id).order_by(
                ManagementProfile.sequence_id.desc()).first()
            if last_in_order_profile:
                last_in_order_sequence_id = last_in_order_profile.sequence_id
                # assign the sequence_id as new highest in order sequence_id
                data.sequence_id = last_in_order_sequence_id + 1
            else:
                data.sequence_id = 1
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
                # Key (account_profile_id)=(25) is not present in \
                # table "account_profile".
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

    @swag_from('swagger_docs/management_profile_put.yml')
    def put(self, row_id):
        """
        Update a Management Profile
        """
        management_profile_schema = ManagementProfileSchema()
        # first find model
        model = None
        try:
            model = ManagementProfile.query.get(row_id)
            if model is None:
                c_abort(404, message='Management Profile id:'
                        '%s does not exist' % str(row_id))
            # check ownership
            if (model.account_profile.account_id !=
                    g.current_user['account']['row_id']):
                abort(403)
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
                detect_type=True, type_only=True,
                not_local=True)
            if ferrors:
                db.session.rollback()
                return ferrors['message'], ferrors['code']
            file_data['files'][fname] = fpath
        # delete files
        if 'profile_photo' in request.form and request.form['profile_photo']:
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
                    # when profile photo delete profile thumbnail also delete
                    if model.profile_thumbnail:
                        th_errors = delete_files(
                            [model.profile_thumbnail], sub_folder=sub_folder,
                            full_folder=profile_photo_full_folder,
                            is_thumbnail=True)
                        if th_errors:
                            return th_errors['message'], th_errors['code']

        try:
            # get the json data from the request
            json_data = request.form.to_dict()

            if (not json_data and  # <- no text data
                    not file_data['files'] and  # <- no profile photo upload
                    'delete' not in file_data):  # no profile photo delete
                # no data of any sort
                c_abort(400)

            # validate and deserialize input
            data, errors = management_profile_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)

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

            # no errors, so update data to db
            data.account_profile_id = g.current_user['account_profile_id']
            db.session.add(data)
            db.session.commit()
            if fpath:
                convert_file_into_thumbnail.s(
                    True, data.row_id, APP.MOD_MGMT_PROFILE,
                    fpath, 'profile').delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (account_profile_id)=(25) is not present in \
                # table "account_profile".
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

        return {'message': 'Updated Management Profile'
                'Parameter id: %s' % str(row_id)}, 200

    @swag_from('swagger_docs/management_profile_delete.yml')
    def delete(self, row_id):
        """
        Delete a Management Profile
        """
        model = None
        try:
            # first find model
            model = ManagementProfile.query.get(row_id)
            if model is None:
                c_abort(404, message='Management Profile '
                        'id: %s does not exist' % str(row_id))
            # check ownership
            if (model.account_profile.account_id !=
                    g.current_user['account']['row_id']):
                abort(403)
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

    @swag_from('swagger_docs/management_profile_get.yml')
    def get(self, row_id):
        """
        Get a Management Profile by id
        """
        management_profile_schema = ManagementProfileSchema()
        model = None
        try:
            # first find model
            model = ManagementProfile.query.get(row_id)
            if model is None:
                c_abort(404, message='Management Profile id:'
                        ' %s does not exist' % str(row_id))
            # check ownership
            if (model.account_profile.account_id !=
                    g.current_user['account']['row_id']):
                abort(403)
            result = management_profile_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class ManagementProfileListAPI(AuthResource):
    """
    Read API for management profile lists, i.e, more than 1 profile
    """
    model_class = ManagementProfile

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['profile_photo_url']
        super(ManagementProfileListAPI, self).__init__(*args, **kwargs)

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
        # build specific extra queries filters
        if extra_query:
            pass

        query = self._build_final_query(query_filters, query_session, operator)

        query = query.options(joinedload(ManagementProfile.account_profile))

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/management_profile_get_list.yml')
    def get(self):
        """
        Get the list
        """
        management_profile_read_schema = ManagementProfileReadArgsSchema(
            strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            management_profile_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(ManagementProfile), operator)
            # making a copy of the main output schema
            management_profile_schema = ManagementProfileSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                management_profile_schema = ManagementProfileSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching management profiles found')
            result = management_profile_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class ManagementProfileOrderAPI(AuthResource):
    """
    PUT API for management profile ordering according to their sequence_id
    """

    @swag_from('swagger_docs/management_profile_order_put.yml')
    def put(self):
        """
        update the management_profiles's sequence_id
        """
        management_profile_order_schema = ManagementProfileOrderSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input
            data, errors = management_profile_order_schema.load(json_data)
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
