"""
API endpoints for "corporate announcements" package.
"""
import os

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.orm import load_only, joinedload, aliased
from flasgger import swag_from
from sqlalchemy import and_, null, func, asc, desc, or_

from app import db, c_abort, corporateannouncementfile
from app.base.api import AuthResource, BaseResource
from app.common.helpers import store_file, delete_files
from app.common.utils import get_s3_download_link, do_nothing
from app.resources.corporate_announcements.models import (
    CorporateAnnouncement)
from app.resources.corporate_announcements.schemas import (
    CorporateAnnouncementSchema, CorporateAnnouncementReadArgsSchema, GlobalAnnouncementReadArgsSchema,
    GlobalAnnouncementSchema)
from app.resources.corporate_announcements.helpers import (
    check_cfollow_exists)
from app.resources.follows.models import CFollow
from app.resources.accounts.models import Account
from app.resources.accounts import constants as ACCOUNT
from app.resources.user_profiles.models import UserProfile
from app.resources.users.models import User
from app.resources.bse.models import BSEFeed
from app.resources.descriptor.models import BSE_Descriptor
from app.resources.corporate_announcements_category.models import CorporateAnnouncementCategory
from queueapp.corporate_announcements.notification_tasks import add_corporate_announcement_notification
from app.resources.notifications import constants as NOTIFY


# main input and output schema
corporate_schema = CorporateAnnouncementSchema()
# schema for reading get arguments
corporate_read_schema = CorporateAnnouncementReadArgsSchema(strict=True)


class CorporateAnnouncementAPI(AuthResource):
    """
    For creating new corporate announcement
    """

    @swag_from('swagger_docs/corporate_announcement_post.yml')
    def post(self):
        """
        Create corporate announcement
        """
        corporate_schema = CorporateAnnouncementSchema()
        # get the form data from the request
        json_data = request.form
        if not json_data:
            c_abort(400)

        try:
            data, errors = corporate_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            if (g.current_user['is_admin'] is not True and
                    g.current_user['account_type'] != ACCOUNT.ACCT_CORPORATE):
                c_abort(403)

            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.account_id = g.current_user['account_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()

        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        file_data = {'files': {}}
        sub_folder = data.file_subfolder_name()
        file_full_folder = data.full_folder_path(
            CorporateAnnouncement.root_file_folder_key)
        if 'file' in request.files:
            # new file being added
            # add new file
            fpath, fname, ferrors, ftype = store_file(
                corporateannouncementfile, request.files['file'],
                sub_folder=sub_folder, full_folder=file_full_folder,
                detect_type=True, type_only=True)
            if ferrors:
                db.session.delete(data)
                db.session.commit()
                return ferrors['message'], ferrors['code']
            file_data['files'][fname] = fpath
        # delete files
        if 'file' in request.form:
            file_data['delete'] = []
            if request.form['file'] == data.file:
                file_data['delete'].append(
                    request.form['file'])
                if file_data['delete']:
                    # delete all mentioned files
                    ferrors = delete_files(
                        file_data['delete'], sub_folder=sub_folder,
                        full_folder=file_full_folder)
                    if ferrors:
                        return ferrors['message'], ferrors['code']

        try:
            if file_data and (file_data['files'] or 'delete' in file_data):
                # populate db data from file_data
                # parse new files
                if file_data['files']:
                    data.file = [
                        fname for fname in file_data['files']][0]

            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
            if data.account_id != None:
                add_corporate_announcement_notification.s(True, data.row_id, NOTIFY.NT_GENERAL_CORP_ANNOUNCEMENT).delay()

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

        return {'message': 'Corporate Announcement created: %s' %
                           str(data.row_id), 'row_id': data.row_id}, 201

    @swag_from('swagger_docs/corporate_announcement_put.yml')
    def put(self, row_id):
        """
        Update Corporate announcement
        """
        corporate_schema = CorporateAnnouncementSchema()
        model = None
        try:
            model = CorporateAnnouncement.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Corporate Announcement id: %s'
                                     ' does not exist' % str(row_id))

            if model.created_by != g.current_user['row_id']:
                abort(403)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        # get the json data from the request
        json_data = request.form
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input
            data, errors = corporate_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        file_data = {'files': {}}
        sub_folder = data.file_subfolder_name()
        file_full_folder = data.full_folder_path(
            CorporateAnnouncement.root_file_folder_key)
        if 'file' in request.files:
            # new file being added
            # add new file
            fpath, fname, ferrors, ftype = store_file(
                corporateannouncementfile, request.files['file'],
                sub_folder=sub_folder,
                full_folder=file_full_folder,
                detect_type=True, type_only=True)
            if ferrors:
                return ferrors['message'], ferrors['code']
            file_data['files'][fname] = fpath
        # delete files
        if 'file' in request.form:
            file_data['delete'] = []
            if request.form['file'] == data.file:
                file_data['delete'].append(
                    request.form['file'])
                if file_data['delete']:
                    # delete all mentioned files
                    ferrors = delete_files(
                        file_data['delete'], sub_folder=sub_folder,
                        full_folder=file_full_folder)
                    if ferrors:
                        return ferrors['message'], ferrors['code']

        try:
            if file_data and (file_data['files'] or 'delete' in file_data):
                # populate db data from file_data
                # parse new files
                if file_data['files']:
                    data.file = [
                        fname for fname in file_data['files']][0]

                # any old files to delete
                if 'delete' in file_data:
                    for file in file_data['delete']:
                        if file == data.file:
                            data.file = None

            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Updated Corporate Announcement id: %s' %
                           str(row_id)}, 200

    @swag_from('swagger_docs/corporate_announcement_delete.yml')
    def delete(self, row_id):
        """
        Delete a corporate announcement
        """
        model = None
        try:
            # first find model
            model = CorporateAnnouncement.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Corporate Announcement id: %s'
                        ' does not exist' % str(row_id))
            if model.created_by != g.current_user['row_id']:
                abort(403)
            # if model is found, and not yet deleted, delete it
            model.updated_by = g.current_user['row_id']
            model.deleted = True
            db.session.add(model)
            db.session.commit()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204

    @swag_from('swagger_docs/corporate_announcement_get.yml')
    def get(self, row_id):
        """
        Get a corporate announcement request by id
        """
        model = None
        try:
            # first find model
            model = CorporateAnnouncement.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Corporate Announcement id: %s'
                                     ' does not exist' % str(row_id))
            result = CorporateAnnouncementSchema().dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class CorporateAnnouncementNoAuthAPI(BaseResource):

    def get(self, row_id):
        """
        Get a corporate announcement request by id
        """
        try:
            # first find model
            model = CorporateAnnouncement.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Corporate Announcement id: %s'
                                     ' does not exist' % str(row_id))
            result = CorporateAnnouncementSchema(
                only=CorporateAnnouncementSchema._open_api_s_proj).dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data}, 200


class CorporateAnnouncementListAPI(AuthResource):
    """
    Read API for corporate announcement lists, i.e, more than 1
    """
    model_class = CorporateAnnouncement

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = [
            'account', 'creator', 'editor', 'ca_event_transcript_file',
            'file_url', 'ca_event_audio_file', 'ec_category']
        super(CorporateAnnouncementListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        category = None
        categories = None
        category_id = None
        if 'category' in filters and filters['category']:
            category = filters.pop('category')
        if 'categories' in filters and filters['categories']:
            categories = filters.pop('categories')
        if 'category_id' in filters and filters['category_id']:
            category_id = filters.pop('category_id')
        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)
        # build specific extra queries filters
        account_id = None
        following_query = None
        if extra_query:
            if 'company_id' in extra_query and extra_query['company_id']:
                account_id = extra_query.pop('company_id')
            if 'following' in extra_query and extra_query['following']:
                following_query = self._build_final_query(
                    query_filters, query_session, operator)

        if account_id:
            query_filters['base'].append(
                CorporateAnnouncement.account_id == account_id)
        else:
            query_filters['base'].append(
                CorporateAnnouncement.account_id == g.current_user[
                    'account_id'])
        if category:
            query_filters['base'].append(
                and_(CorporateAnnouncement.category == category))

        query = self._build_final_query(
            query_filters, query_session, operator)

        query = query.options(
            joinedload(CorporateAnnouncement.account).
            joinedload(Account.profile),
            joinedload(CorporateAnnouncement.creator).load_only(
                'row_id', 'account_id').joinedload(
                User.account).joinedload(Account.profile))

        if categories:
            query = query.filter(CorporateAnnouncement.category.in_(categories))

        if category_id:
            query = query.filter(CorporateAnnouncement.category_id == int(category_id))

        if following_query:
            following_query = following_query.join(
                CFollow, CFollow.company_id == CorporateAnnouncement.account_id
            ).filter(CFollow.sent_by == g.current_user['row_id'])

            final_query = query.union(following_query)
        # else:
        #     final_query = query
        else:
            final_query = query.join(BSE_Descriptor, CorporateAnnouncement.bse_descriptor ==
                                     BSE_Descriptor.descriptor_id, isouter=True)

        if not db_projection:
            db_projection = []
        if not s_projection:
            s_projection = []

        return final_query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/corporate_announcement_get_list.yml')
    def get(self):
        """
        Get the list
        """
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            corporate_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(CorporateAnnouncement),
                                 operator)
            # making a copy of the main output schema
            corporate_schema = CorporateAnnouncementSchema(
                exclude=CorporateAnnouncementSchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                corporate_schema = CorporateAnnouncementSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching corporate'
                                     ' announcement found')
            result = corporate_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class CorporateAnnouncementNoAuthListAPI(BaseResource):
    """
    Read API for corporate announcement lists, i.e, more than 1
    """
    model_class = CorporateAnnouncement

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = [
            'account', 'creator', 'editor', 'ca_event_transcript_file',
            'file_url', 'ca_event_audio_file']
        super(CorporateAnnouncementNoAuthListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        category = None
        if 'category' in filters and filters['category']:
            category = filters.pop('category')
        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)
        # build specific extra queries filters
        account_id = None
        if extra_query:
            if 'company_id' in extra_query and extra_query['company_id']:
                account_id = extra_query.pop('company_id')

        if account_id:
            query_filters['base'].append(
                CorporateAnnouncement.account_id == account_id)

        if category:
            query_filters['base'].append(
                and_(CorporateAnnouncement.category == category))
        query = self._build_final_query(
            query_filters, query_session, operator)

        query = query.options(
            joinedload(CorporateAnnouncement.account).load_only(
                'account_name'))

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/corporate_announcement_get_list.yml')
    def get(self):
        """
        Get the list
        """
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            corporate_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(CorporateAnnouncement),
                                 operator)
            db_projection = CorporateAnnouncementSchema._open_api_db_proj
            # making a copy of the main output schema
            corporate_schema = CorporateAnnouncementSchema(
                only=CorporateAnnouncementSchema._open_api_s_proj)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                corporate_schema = CorporateAnnouncementSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching corporate'
                                     ' announcement found')
            result = corporate_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200