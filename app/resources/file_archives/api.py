"""
API endpoints for "file archives" package.
"""

import os

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.orm import load_only, joinedload
from sqlalchemy import and_, null, func, or_, literal
from flask_uploads import AUDIO
from flasgger.utils import swag_from

from app import db, c_abort, archivefile
from app.base.api import AuthResource
from app.base import constants as BASE
from app.common.helpers import (
    store_file, delete_files, file_type_for_thumbnail, delete_fs_file)
from app.resources.file_archives.models import ArchiveFile
from app.resources.file_archives.schemas import (
    ArchiveFileSchema,
    ArchiveFileReadArgsSchema,
    ArchiveFileLibrarySchema)
from app.resources.file_archives.helpers import add_logo_url
from app.resources.users import constants as USER
from app.resources.accounts import constants as ACCOUNT
from app.activity.activities.models import activityfile
from app.corporate_access_resources.corporate_access_events.models import corporateaccesseventfiles,CorporateAccessEvent
from app.corporate_access_resources.corporate_access_event_participants.models import CorporateAccessEventParticipant
from app.corporate_access_resources.corporate_access_event_hosts.models import CorporateAccessEventHost
from app.corporate_access_resources.corporate_access_event_invitees.models import CorporateAccessEventInvitee
from app.webcast_resources.webcasts.models import webcastfile, Webcast
from app.webcast_resources.webcast_participants.models import WebcastParticipant
from app.webcast_resources.webcast_invitees.models import WebcastInvitee
from app.webcast_resources.webcast_hosts.models import WebcastHost
from app.webinar_resources.webinars.models import webinarfile
from app.webinar_resources.webinar_hosts.models import WebinarHost
from app.webinar_resources.webinar_invitees.models import WebinarInvitee
from app.webinar_resources.webinar_participants.models import WebinarParticipant
from app.resources.users.models import User

from queueapp.user_stats_tasks import manage_users_stats
from queueapp.thumbnail_tasks import convert_file_into_thumbnail


class ArchiveFileAPI(AuthResource):
    """
    Create, update, delete API for archive files
    """
    @swag_from('swagger_docs/file_archive_post.yml')
    def post(self):
        """
        Create a file
        """
        archive_file_schema = ArchiveFileSchema()
        # get the json data from the request
        json_data = {}

        try:
            # validate and deserialize input into object
            data, errors = archive_file_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
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

        file_data = {'files': {}, 'types': {}}
        sub_folder = data.file_subfolder_name()
        full_folder = data.full_folder_path()
        if 'filename' in request.files:
            # new file being added
            # add new file
            fpath, fname, ferrors, ftype = store_file(
                archivefile, request.files['filename'], sub_folder=sub_folder,
                full_folder=full_folder, detect_type=True, type_only=True,
                not_local=True)
            if ferrors:
                db.session.delete(data)
                db.session.commit()
                return ferrors['message'], ferrors['code']
            file_data['files'][fname] = fpath
            file_data['types'][fname] = ftype
        else:
            db.session.delete(data)
            db.session.commit()
            c_abort(400, message='No file provided')

        try:
            if file_data and (file_data['files'] or 'delete' in file_data):
                # populate db data from file_data
                # parse new files
                if file_data['files']:
                    data.filename = [fname for fname in file_data['files']][0]
                    data.file_type = file_data['types'][data.filename]
                    # major file type according to file extension
                    fmtype = (os.path.basename(fname)).split('.')[-1]
                    if fmtype in BASE.VIDEO:
                        data.file_major_type = BASE.FILETYP_VD
                    elif fmtype in AUDIO:
                        data.file_major_type = BASE.FILETYP_AD
                    else:
                        data.file_major_type = BASE.FILETYP_OT
            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
            # for change user total_video
            # #TODO: used in future
            fmtype = (os.path.basename(fname)).split('.')[-1]
            if fmtype in BASE.VIDEO:
                manage_users_stats.s(
                    True, data.created_by, USER.USR_VIDEOS).delay()
            # for change user total_file
            manage_users_stats.s(
                True, data.created_by, USER.USR_FILES).delay()
            # for thumbnail conversion
            if file_type_for_thumbnail(fname):
                convert_file_into_thumbnail.s(
                    True, data.row_id, BASE.MOD_ARCHIVE, fpath).delay()
            else:
                delete_fs_file(fpath)
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

    @swag_from('swagger_docs/file_archive_put.yml')
    def put(self, row_id):
        """
        Update a archive file, pass file data as multipart-form
        """
        archive_file_schema = ArchiveFileSchema()
        # first find model
        model = None
        try:
            model = ArchiveFile.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='File id: %s does not exist' %
                                     str(row_id))

            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
        except Forbidden as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        json_data = request.form
        file_data = {'files': {}, 'types': {}}
        sub_folder = model.file_subfolder_name()
        full_folder = model.full_folder_path()
        if not json_data and 'filename' not in request.files:
            c_abort(400)

        if 'filename' in request.files:
            # new file being added
            # check if there is already a file, then delete it, then add new
            if model.filename:
                ferrors = delete_files(
                    [model.filename], sub_folder=sub_folder,
                    full_folder=full_folder)
                if ferrors:
                    return ferrors['message'], ferrors['code']
            # add new file
            fpath, fname, ferrors, ftype = store_file(
                archivefile, request.files['filename'], sub_folder=sub_folder,
                full_folder=full_folder, detect_type=True, type_only=True)
            if ferrors:
                return ferrors['message'], ferrors['code']
            file_data['files'][fname] = fpath
            file_data['types'][fname] = ftype

        try:
            if file_data and (file_data['files'] or 'delete' in file_data):
                # populate db data from file_data
                data = model
                # parse new files
                if file_data['files']:
                    data.filename = [fname for fname in file_data['files']][0]
                    data.file_type = file_data['types'][data.filename]
            if json_data:
                # validate and deserialize input
                data, errors = archive_file_schema.load(
                    json_data, instance=model, partial=True)
                if errors:
                    c_abort(422, errors=errors)
            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Updated File id: %s' % str(row_id)}, 200

    @swag_from('swagger_docs/file_archive_delete.yml')
    def delete(self, row_id):
        """
        Delete a file
        """
        model = None
        try:
            # first find model
            model = ArchiveFile.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='File id: %s does not exist' %
                                     str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)

            # if model is found, and not yet deleted, delete it
            model.deleted = True
            db.session.add(model)
            db.session.commit()

            if model.file_type in BASE.VIDEO:
                manage_users_stats.s(
                    True, model.created_by, USER.USR_VIDEOS,
                    increase=False).delay()
            # for change user total_file
            manage_users_stats.s(
                True, model.created_by, USER.USR_FILES,
                increase=False).delay()
            # delete file from s3
            # #TODO:used in future
            # fully_delete_file.s(True, model.row_id).delay()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204

    @swag_from('swagger_docs/file_archive_get.yml')
    def get(self, row_id):
        """
        Get a file by id
        """
        archive_file_schema = ArchiveFileSchema()
        model = None
        try:
            # first find model
            model = ArchiveFile.query.options(joinedload(
                ArchiveFile.account)).get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='File id: %s does not exist' %
                                     str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            result = archive_file_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result}, 200


class ArchiveFileListAPI(AuthResource):
    """
    Read API for library file lists, i.e, more than 1 library file
    """
    model_class = ArchiveFile

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['filename_url', 'linked_contacts']
        super(ArchiveFileListAPI, self).__init__(*args, **kwargs)

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
        account_id = None
        if extra_query:
            if 'company_id' in extra_query and extra_query['company_id']:
                if g.current_user['account']['account_type'] != \
                        ACCOUNT.ACCT_CORPORATE:
                    account_id = extra_query.pop('company_id')

        if account_id:
            query_filters['base'].append(
                ArchiveFile.account_id == account_id)
        else:
            query_filters['base'].append(
                ArchiveFile.created_by == g.current_user['row_id'])

        query = self._build_final_query(query_filters, query_session, operator)

        query = query.options(joinedload(ArchiveFile.account))

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/file_archive_get_list.yml')
    def get(self):
        """
        Get the list
        """
        archive_file_read_schema = ArchiveFileReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            archive_file_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(ArchiveFile), operator)
            # making a copy of the main output schema
            archive_file_schema = ArchiveFileSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                archive_file_schema = ArchiveFileSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching files found')
            result = archive_file_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class ArchiveFileLibraryListAPI(AuthResource):
    """
    Read API for library file lists, i.e, more than 1 library file
    """
    model_class = ArchiveFile

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['filename_url', 'linked_contacts']
        super(ArchiveFileLibraryListAPI, self).__init__(*args, **kwargs)

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

        query_filters_union_webcast = {}
        query_filters_union_webcast['base'] = query_filters['base'][:]
        query_filters_union_webcast['filters'] = query_filters['filters'][:]

        query_filters_union_webinar = {}
        query_filters_union_webinar['base'] = query_filters['base'][:]
        query_filters_union_webinar['filters'] = query_filters['filters'][:]

        query_filters_union_activity = {}
        query_filters_union_activity['base'] = query_filters['base'][:]
        query_filters_union_activity['filters'] = query_filters['filters'][:]
        # build specific extra queries filters
        module_name = None
        if extra_query:
            if 'module_name' in extra_query and extra_query['module_name']:
                module_name = extra_query.pop('module_name')

        # base filter for different modules
        query_filters_union_activity['base'].append(
        ArchiveFile.created_by == g.current_user['row_id'])

        query_filters['base'].append(
        or_(ArchiveFile.created_by == g.current_user['row_id'],
            CorporateAccessEventParticipant.participant_id == g.current_user['row_id'],
            CorporateAccessEventHost.host_id == g.current_user['row_id'],
            CorporateAccessEventInvitee.invitee_id == g.current_user['row_id']))

        query_filters_union_webcast['base'].append(
        or_(ArchiveFile.created_by == g.current_user['row_id'],
            WebcastParticipant.participant_id == g.current_user['row_id'],
            WebcastHost.host_id == g.current_user['row_id'],
            WebcastInvitee.invitee_id == g.current_user['row_id']))

        query_filters_union_webinar['base'].append(
        or_(ArchiveFile.created_by == g.current_user['row_id'],
            WebinarParticipant.participant_id == g.current_user['row_id'],
            WebinarHost.host_id == g.current_user['row_id'],
            WebinarInvitee.invitee_id == g.current_user['row_id']))

        # make final query for different modules
        query = self._build_final_query(query_filters, query_session, operator)
        query_for_union_webcast = self._build_final_query(query_filters_union_webcast, query_session, operator)
        query_for_union_webinar = self._build_final_query(query_filters_union_webinar, query_session, operator)
        query_for_union_activity = self._build_final_query(query_filters_union_activity, query_session, operator)

        activity_query = query_for_union_activity.join(
            activityfile, activityfile.c.file_id==ArchiveFile.row_id).with_entities(
            ArchiveFile.created_date, ArchiveFile.filename,
            ArchiveFile.created_by, ArchiveFile.row_id,
            ArchiveFile.file_type,
            literal('Activity').label('module_name')).distinct()
        corporate_query = query.join(
            corporateaccesseventfiles,
            corporateaccesseventfiles.c.file_id==ArchiveFile.row_id).join(
            CorporateAccessEventParticipant,
            CorporateAccessEventParticipant.corporate_access_event_id==
            corporateaccesseventfiles.c.corporate_access_event_id, isouter=True).join(
            CorporateAccessEventHost,
            CorporateAccessEventHost.corporate_access_event_id ==
            corporateaccesseventfiles.c.corporate_access_event_id, isouter=True).join(
            CorporateAccessEventInvitee,
            CorporateAccessEventInvitee.corporate_access_event_id ==
            corporateaccesseventfiles.c.corporate_access_event_id, isouter=True).with_entities(
            ArchiveFile.created_date, ArchiveFile.filename,
            ArchiveFile.created_by, ArchiveFile.row_id,
            ArchiveFile.file_type,
            literal('CorporateAccessEvent').label('module_name')).distinct()
        webcast_query = query_for_union_webcast.join(
            webcastfile, webcastfile.c.file_id == ArchiveFile.row_id).join(
            WebcastParticipant, WebcastParticipant.webcast_id ==
            webcastfile.c.webcast_id, isouter=True).join(
            WebcastHost,
            WebcastHost.webcast_id == webcastfile.c.webcast_id, isouter=True).join(
            WebcastInvitee,
            WebcastInvitee.webcast_id == webcastfile.c.webcast_id, isouter=True).with_entities(
            ArchiveFile.created_date, ArchiveFile.filename,
            ArchiveFile.created_by, ArchiveFile.row_id,
            ArchiveFile.file_type,
            literal('Webcast').label('module_name')).distinct()
        webinar_query = query_for_union_webinar.join(
            webinarfile,
            webinarfile.c.file_id==ArchiveFile.row_id).join(
            WebinarParticipant,
            WebinarParticipant.webinar_id==
            webinarfile.c.webinar_id, isouter=True).join(
            WebinarHost,
            WebinarHost.webinar_id ==
            webinarfile.c.webinar_id, isouter=True).join(
            WebinarInvitee,
            WebinarInvitee.webinar_id ==
            webinarfile.c.webinar_id, isouter=True).with_entities(
            ArchiveFile.created_date, ArchiveFile.filename,
            ArchiveFile.created_by, ArchiveFile.row_id,
            ArchiveFile.file_type,
            literal('Webinar').label('module_name')).distinct()

        # consider query with respect to filter applied by user using module name
        if module_name == 'activity':
            query = activity_query
        elif module_name == 'corporate-access-event':
            query = corporate_query
        elif module_name == 'webcast':
            query = webcast_query
        elif module_name == 'webinar':
            query = webinar_query
        else:
            query = activity_query.union_all(corporate_query).union_all(webcast_query).union_all(webinar_query)

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/file_archive_get_list.yml')
    def get(self):
        """
        Get the list
        """
        archive_file_read_schema = ArchiveFileReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            archive_file_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(ArchiveFile), operator)
            # making a copy of the main output schema
            archive_file_schema = ArchiveFileLibrarySchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                archive_file_schema = ArchiveFileLibrarySchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching files found')
            result = archive_file_schema.dump(models, many=True)
            result_url = add_logo_url(result.data)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200