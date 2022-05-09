"""
API endpoints for "corporate announcements" package.
"""
import os
import uuid
import xml.etree.ElementTree as ET
from flashtext import KeywordProcessor

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy import and_, func
from sqlalchemy.orm import load_only, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy.inspection import inspect
from flasgger import swag_from

from app import (
    db, c_abort, corporateannouncementfile, corporateannouncementxmlfile)
from app.base.api import AuthResource
from app.base import constants as APP
from app.common.helpers import store_file, delete_files, save_files_locally
from app.auth.decorators import role_permission_required
from app.resources.corporate_announcements.models import (
    CorporateAnnouncement)
from app.resources.corporate_announcements.schemas import (
    AdminCorporateAnnouncementSchema,
    CorporateAnnouncementReadArgsSchema)
from app.resources.corporate_announcements_category.models import CorporateAnnouncementCategory
from app.resources.account_managers.models import AccountManager
from app.resources.accounts.models import Account
from app.resources.users.models import User
from app.resources.roles import constants as ROLE
from app.resources.corporate_announcements import constants as CATEGORY
from queueapp.corporate_announcements.notification_tasks import add_corporate_announcement_notification
from app.resources.notifications import constants as NOTIFY


class AdminCorporateAnnouncementAPI(AuthResource):
    """
    For creating new corporate announcement by admin
    """
    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA])
    @swag_from('swagger_docs/admin_corporate_announcement_post.yml')
    def post(self):
        """
        Create corporate announcement by admin
        """
        # main input and output schema
        admin_corporate_schema = AdminCorporateAnnouncementSchema()
        # get the json data from the request
        json_data = request.form
        if not json_data:
            c_abort(400)

        try:
            data, errors = admin_corporate_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()

        except IntegrityError as e:
            # format of the message:
            # Key (account_id)=(17) is not present in table account
            column = e.orig.diag.message_detail.split('(')[1][:-2]
            db.session.rollback()
            c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
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
                add_corporate_announcement_notification.s(True, data.row_id,NOTIFY.NT_GENERAL_CORP_ANNOUNCEMENT).delay()

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

    @role_permission_required(perms=[ROLE.EPT_AA],  roles=[
        ROLE.ERT_SU, ROLE.ERT_CA])
    @swag_from('swagger_docs/admin_corporate_announcement_put.yml')
    def put(self, row_id):
        """
        Update Corporate announcement by admin
        """
        admin_corporate_schema = AdminCorporateAnnouncementSchema()
        model = None
        try:
            model = CorporateAnnouncement.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Corporate Announcement id: %s'
                                     ' does not exist' % str(row_id))
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
            data, errors = admin_corporate_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()
        except Forbidden as e:
            raise e
        except IntegrityError as e:
            # format of the message:
            # Key (account_id)=(17) is not present in table account
            column = e.orig.diag.message_detail.split('(')[1][:-2]
            db.session.rollback()
            c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
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

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA])
    @swag_from('swagger_docs/admin_corporate_announcement_delete.yml')
    def delete(self, row_id):
        """
        Delete a corporate announcement by admin
        """
        model = None
        try:
            # first find model
            model = CorporateAnnouncement.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Corporate Announcement id: %s'
                        ' does not exist' % str(row_id))
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

    @role_permission_required(perms=[ROLE.EPT_AA])
    @swag_from('swagger_docs/admin_corporate_announcement_get.yml')
    def get(self, row_id):
        """
        Get a corporate announcement request by id by admin
        """
        admin_corporate_schema = AdminCorporateAnnouncementSchema()
        model = None
        try:
            # first find model
            model = CorporateAnnouncement.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Corporate Announcement id: %s'
                                     ' does not exist' % str(row_id))
            result = admin_corporate_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200

class AdminCorporateBulkAnnouncementAPI(AuthResource):
    """
    For update bulk announcement by admin
    """
    @role_permission_required(perms=[ROLE.EPT_AA],  roles=[
        ROLE.ERT_SU, ROLE.ERT_CA])
    # @swag_from('swagger_docs/admin_corporate_announcement_put.yml')
    def put(self):
        """
        Update Corporate announcement by admin
        """
        admin_corporate_schema = AdminCorporateAnnouncementSchema()
        model = None

        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        if not json_data["announcements"]:
            c_abort(422,message='Corporate Announcements does not exist')
        announcements_list = json_data["announcements"]
        try:
            # TODO :-- Apply schema for announcement list
            for announcement in announcements_list:

                if  "row_id" in announcement.keys():
                    model = CorporateAnnouncement.query.get(announcement["row_id"])
                    if model is None or model.deleted:
                        c_abort(404, message='Corporate Announcement id: %s'
                                             ' does not exist' % str(announcement["row_id"]))
                    data, errors = admin_corporate_schema.load(
                        announcement, instance=model,partial=True)
                    if errors:
                        c_abort(422, errors=errors)
                    # no errors, so add data to db
                    data.updated_by = g.current_user['row_id']
                    db.session.add(data)
                    db.session.commit()
                else:
                    c_abort(422,message='row_id does not exist in Corporate Announcements')

        except Forbidden as e:
            raise e
        except IntegrityError as e:
            # format of the message:
            # Key (account_id)=(17) is not present in table account
            column = e.orig.diag.message_detail.split('(')[1][:-2]
            db.session.rollback()
            c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Corporate Announcements are updated'}, 200


class AdminCorporateAnnouncementListAPI(AuthResource):
    """
    Read API for library file lists, i.e, more than 1 library file
    """
    model_class = CorporateAnnouncement

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = [
            'account', 'creator', 'editor', 'ca_event_transcript_file',
            'file_url', 'ca_event_audio_file']
        super(
            AdminCorporateAnnouncementListAPI, self).__init__(*args, **kwargs)

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
        mapper = inspect(CorporateAnnouncement)
        # build specific extra queries filters
        account_id = None
        if extra_query:
            if 'company_id' in extra_query and extra_query['company_id']:
                account_id = extra_query.pop('company_id')
            if 'company_name' in extra_query and extra_query['company_name']:
                query_filters['filters'].append(
                    func.lower(Account.account_name).like(
                        "%" + extra_query['company_name'].lower() + "%"))

        if account_id:
            query_filters['base'].append(
                CorporateAnnouncement.account_id == account_id)
        if category:
            query_filters['base'].append(
                and_(CorporateAnnouncement.category == category))
        query = self._build_final_query(
            query_filters, query_session, operator)

        if 'account_name' in sort['sort_by']:
            mapper = inspect(Account)
        if sort:
            sort_fxn = 'asc'
            if sort['sort'] == 'dsc':
                sort_fxn = 'desc'
            for sby in sort['sort_by']:
                if sby in mapper.columns:
                    order.append(getattr(mapper.columns[sby], sort_fxn)())

        query = query.options(
            joinedload(CorporateAnnouncement.account).
            joinedload(Account.profile),
            joinedload(CorporateAnnouncement.creator).load_only(
                'row_id', 'account_id').joinedload(
                User.account).joinedload(Account.profile))
        query = query.join(
            Account, Account.row_id == CorporateAnnouncement.account_id)
        # manager can access assigned account announcement only
        if g.current_user['role']['name'] == ROLE.ERT_MNG:
            query = query.join(
                AccountManager, and_(
                    CorporateAnnouncement.account_id ==
                    AccountManager.account_id, AccountManager.manager_id ==
                    g.current_user['row_id']))

        return query, db_projection, s_projection, order, paging

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    @swag_from('swagger_docs/admin_corporate_announcement_get_list.yml')
    def get(self):
        """
        Get the list by admin
        """
        # schema for reading get arguments
        admin_corporate_read_schema = CorporateAnnouncementReadArgsSchema(
            strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            admin_corporate_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(CorporateAnnouncement),
                                 operator)
            # making a copy of the main output schema
            admin_corporate_schema = AdminCorporateAnnouncementSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                admin_corporate_schema = AdminCorporateAnnouncementSchema(
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
            result = admin_corporate_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class AdminCorporateBulkAnnouncementAPI(AuthResource):
    """
    For update bulk announcement by admin

    """
    @role_permission_required(perms=[ROLE.EPT_AA],  roles=[
        ROLE.ERT_SU, ROLE.ERT_CA])
    # @swag_from('swagger_docs/admin_corporate_announcement_put.yml')
    def put(self):
        """
        Update Corporate announcement by admin
        """
        admin_corporate_schema = AdminCorporateAnnouncementSchema()
        model = None

        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        if not json_data["announcements"]:
            c_abort(422,message='Corporate Announcements does not exist')
        announcements_list = json_data["announcements"]
        try:
            # TODO :-- Apply schema for announcement list
            for announcement in announcements_list:

                if  "row_id" in announcement.keys():
                    model = CorporateAnnouncement.query.get(announcement["row_id"])
                    if model is None or model.deleted:
                        c_abort(404, message='Corporate Announcement id: %s'
                                             ' does not exist' % str(announcement["row_id"]))
                    data, errors = admin_corporate_schema.load(
                        announcement, instance=model,partial=True)
                    if errors:
                        c_abort(422, errors=errors)
                    # no errors, so add data to db
                    data.updated_by = g.current_user['row_id']
                    db.session.add(data)
                    db.session.commit()
                else:
                    c_abort(422,message='row_id does not exist in Corporate Announcements')

        except Forbidden as e:
            raise e
        except IntegrityError as e:
            # format of the message:
            # Key (account_id)=(17) is not present in table account
            column = e.orig.diag.message_detail.split('(')[1][:-2]
            db.session.rollback()
            c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Corporate Announcements are updated'}, 200


class CorporateAnnouncementXMLAPI(AuthResource):
    """
    For creating new corporate announcement by xml file
    """

    @role_permission_required(perms=[ROLE.EPT_AA])
    def post(self):
        """
        Create corporate announcement
        """
        corporate_schema = AdminCorporateAnnouncementSchema()
        all_errors = {}
        try:
            # announcement category 
            cat_obj = CorporateAnnouncementCategory.query.all()
            subject_dict = {}
            category_dict = {}
            for cat in cat_obj:
                if cat.subject_keywords != None:
                    subject_dict[cat.name] = cat.subject_keywords
                if cat.category_keywords != None:
                    category_dict[cat.name] = cat.category_keywords

            # processor object for subject_keywords
            subject_keyword_processor = KeywordProcessor()
            subject_keyword_processor.add_keywords_from_dict(subject_dict)
            
            # processor object for subject_keywords
            category_keyword_processor = KeywordProcessor()
            category_keyword_processor.add_keywords_from_dict(category_dict)

            for xml_file in request.files.getlist('xml_file'):

                doc_category = None

                json_data = {
                    'announcement_date': None
                }
                all_errors[xml_file.filename] = []

                name = '{}.xml'.format(uuid.uuid4().hex)
                fpath, fname, error = save_files_locally(
                    corporateannouncementxmlfile, xml_file,
                    name=name)
                if error:
                    all_errors[xml_file.filename].append(
                        "Couldn't save file locally")
                    continue
                # create element tree object
                tree = ET.parse(fpath)
                root = tree.getroot()
                mapping = {
                    'ScripCode': 'script_code',
                    'SubjectOfAnnouncement': 'subject',
                    'DescriptionOfAnnouncement': 'description',
                    'AttachmentURL': 'url'
                }

                # iterate announcement_Date
                for item in root:
                    # iterate category
                    if 'SubjectOfAnnouncement' in item.tag:
                        
                        keywords_found = subject_keyword_processor.extract_keywords(item.text)
                        if keywords_found:
                            doc_category = keywords_found[0]

                    if not doc_category and 'CategoryOfAnnouncement' in item.tag:
                        
                        keywords_found = category_keyword_processor.extract_keywords(item.text)
                        if keywords_found:
                            doc_category = keywords_found[0]
    
                    if 'context' in item.tag:
                        for context_child in item.getchildren():
                            if 'period' in context_child.tag:
                                for period_child in context_child.getchildren():
                                    if 'instant' in period_child.tag:
                                        json_data['announcement_date'] =\
                                            period_child.text

                    for key in mapping.keys():
                        if key in item.tag:
                            json_data[mapping.pop(key)] = item.text
                            break

                if not doc_category:
                    json_data['category'] = CATEGORY.CANNC_NEWS
                else:
                    json_data['category'] = doc_category

                os.remove(fpath)
                identifier = str(json_data.pop('script_code')) + '-IN'
                corporate_account = Account.query.filter(
                    Account.identifier == identifier).first()
                if not corporate_account:
                    all_errors[xml_file.filename].append(
                        "No matching account found.")
                    continue

                json_data['account_id'] = corporate_account.row_id
                data, errors = corporate_schema.load(json_data)
                if errors:
                    for field in errors:
                        for err in errors[field]:
                            all_errors[xml_file.filename].append(
                                "{} - {}".format(field, err))
                    continue
                # no errors, so add data to db
                data.created_by = g.current_user['row_id']
                data.updated_by = data.created_by
                db.session.add(data)
                db.session.commit()

        except HTTPException as e:
            raise e

        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Corporate Announcements created',
                'extra_message': all_errors}, 201
