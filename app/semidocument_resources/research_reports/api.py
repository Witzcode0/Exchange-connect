"""
API endpoints for "research reports" package.
"""
import json
import datetime
import os

from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy import and_, func
from sqlalchemy.orm import load_only, joinedload, aliased
from werkzeug.exceptions import Forbidden, HTTPException
from dicttoxml import dicttoxml

from app import db, c_abort, researchreportfile
from app.base.api import AuthResource
from app.common.helpers import store_file, delete_files, upload_file
from app.resources.accounts import constants as ACCOUNT
from app.resources.accounts.models import Account
from app.resources.users.models import User
from app.semidocument_resources.research_reports.models import (
    ResearchReport)
from app.semidocument_resources.research_reports.schemas import (
    ResearchReportSchema, ResearchReportReadArgsSchema)
from app.semidocument_resources.research_reports import \
    constants as RESEARCH_REPORT
from app.base import constants as APP

from queueapp.thumbnail_tasks import convert_file_into_thumbnail

from queueapp.semi_documentation.file_parsing_tasks import (
    parsing_research_report_announcement_file)


class ResearchReportAPI(AuthResource):
    """
    CRUD API for research report
    """

    # @swag_from('swagger_docs/research_report_post.yml')
    def post(self):
        """
        Create research report
        """

        research_report_schema = ResearchReportSchema()
        # get the form data from the request
        json_data = request.form.to_dict()
        if not json_data:
            c_abort(400)

        if 'announcement_ids' in json_data and json_data['announcement_ids']:
            json_data['announcement_ids'] = request.form.getlist(
                'announcement_ids')
        if json_data.get('report_parameters'):
            json_data['report_parameters'] = json.loads(
                json_data['report_parameters'])

        try:
            data, errors = research_report_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            if (#'''not g.current_user['is_admin'] or'''
                    g.current_user['account_type'] !=
                    ACCOUNT.ACCT_SELL_SIDE_ANALYST):
                c_abort(403)

            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.account_id = g.current_user['account_id']
            data.updated_by = data.created_by
            data.research_report_date = datetime.datetime.utcnow()
            db.session.add(data)
            db.session.commit()

            # manage files list
            announcment_ids = []
            if research_report_schema._cached_announcements:
                for cf in research_report_schema._cached_announcements:
                    if cf not in data.announcements:
                        announcment_ids.append(cf.row_id)
                        data.announcements.append(cf)
            for param in research_report_schema._cached_report_params:
                if param not in data.parameters:
                    data.parameters.append(param)
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
            ResearchReport.root_folder_key)
        fpath = None
        if 'file' in request.files:
            # new file being added
            # add new file
            fpath, fname, ferrors, ftype = store_file(
                researchreportfile, request.files['file'],
                sub_folder=sub_folder, full_folder=file_full_folder,
                detect_type=True, type_only=True, not_local=True)
            if ferrors:
                db.session.delete(data)
                db.session.commit()
                return ferrors['message'], ferrors['code']
            file_data['files'][fname] = fpath

        try:
            if file_data and (file_data['files'] or 'delete' in file_data):
                # populate db data from file_data
                # parse new files
                if file_data['files']:
                    data.file = [
                        fname for fname in file_data['files']][0]

            # no errors, so add data to db
            db.session.add(data)

            # past research report for same company will be deleted
            ResearchReport.query.filter(
                ResearchReport.corporate_account_id==data.corporate_account_id,
                ResearchReport.row_id != data.row_id,
                ResearchReport.created_by == g.current_user['row_id']).update(
                {'deleted': True}, synchronize_session=False)
            db.session.commit()
            report_schema = ResearchReportSchema(
                only=ResearchReportSchema._fields_for_xml)
            result = report_schema.dump(data).data
            folder = current_app.config['UPLOADED_RESEARCHREPORTXMLFILE_DEST']
            if not os.path.exists(folder):
                os.makedirs(folder)
            file_name = "research_report_{}.xml".format(data.row_id)
            full_path = os.path.join(folder, file_name)
            with open(full_path, 'wb') as f:
                f.write(dicttoxml(result))
            if current_app.config['S3_UPLOAD']:
                if not upload_file(full_path, file_full_folder):
                    error = 'Could not upload file {}'.format(file_name)
                    current_app.logger.exception(error)
                os.remove(full_path)
                data.xml_file = file_name
                db.session.add(data)
                db.session.commit()
            if fpath:
                if fpath:
                    convert_file_into_thumbnail.s(
                        True, data.row_id, APP.MOD_RESEARCH_REPORT,
                        fpath).delay()
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

        return {'message': 'Research Report created: %s' %
                           str(data.row_id), 'row_id': data.row_id}, 201

    # @swag_from('swagger_docs/corporate_announcement_put.yml')
    def put(self, row_id):
        """
        Update Research report
        """
        research_report_schema = ResearchReportSchema()
        model = None
        try:
            model = ResearchReport.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Research Report id: %s'
                                     ' does not exist' % str(row_id))

            if (#not g.current_user['is_admin'] or
                    g.current_user['account_type'] !=
                    ACCOUNT.ACCT_SELL_SIDE_ANALYST or
                    model.created_by != g.current_user['row_id']):
                c_abort(403)

        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        # get the json data from the request
        json_data = request.form.to_dict()
        if not json_data and not request.files:
            c_abort(400)

        try:
            # validate and deserialize input
            if 'announcement_ids' in json_data and json_data[
                    'announcement_ids']:
                json_data['announcement_ids'] = request.form.getlist(
                    'announcement_ids')
            data, errors = research_report_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()
            # manage files list
            announcment_ids = []
            if research_report_schema._cached_announcements:
                for cf in research_report_schema._cached_announcements:
                    if cf not in data.announcements:
                        announcment_ids.append(cf.row_id)
                        data.announcements.append(cf)
                for oldcf in data.announcements[:]:
                    if oldcf not in research_report_schema._cached_announcements:
                        data.announcements.remove(oldcf)
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
            ResearchReport.root_folder_key)
        fpath = None
        if 'file' in request.files:
            # new file being added
            # add new file
            fpath, fname, ferrors, ftype = store_file(
                researchreportfile, request.files['file'],
                sub_folder=sub_folder, full_folder=file_full_folder,
                detect_type=True, type_only=True, not_local=True)
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
            if fpath:
                convert_file_into_thumbnail.s(
                    True, data.row_id, APP.MOD_RESEARCH_REPORT, fpath).delay()
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        data.load_urls()
        return {'message': 'Updated Corporate Announcement id: %s' %
                           str(row_id), 'file_url': data.file_url}, 200

    # @swag_from('swagger_docs/corporate_announcement_delete.yml')
    def delete(self, row_id):
        """
        Delete a research report
        """
        try:
            # first find model
            model = ResearchReport.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Research Report id: %s'
                        ' does not exist' % str(row_id))

            if (#not g.current_user['is_admin'] or
                    g.current_user['account_type'] !=
                    ACCOUNT.ACCT_SELL_SIDE_ANALYST or
                    model.created_by != g.current_user['row_id']):
                c_abort(403)

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

    # @swag_from('swagger_docs/corporate_announcement_get.yml')
    def get(self, row_id):
        """
        Get a research report by id
        """
        result = None
        try:
            # first find model
            model = ResearchReport.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Research Report id: %s'
                                     ' does not exist' % str(row_id))
            result = ResearchReportSchema().dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class ResearchReportListAPI(AuthResource):
    """
    Read API for research report lists, i.e, more than 1
    """
    model_class = ResearchReport

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['account', 'creator', 'editor',
                                    'corporate_account']
        super(ResearchReportListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        # build specific extra queries filters
        corporate_account_id = None
        account_id = None
        if ('corporate_account_id' in filters
                and filters['corporate_account_id']):
            corporate_account_id = filters.pop('corporate_account_id')
        if ('account_id' in filters
                and filters['account_id']):
            account_id = filters.pop('account_id')
        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)

        AccountCorporate = aliased(Account, name='AccountCorporate')
        CrossAccount = Account if corporate_account_id else AccountCorporate
        company_name = None
        main_filter = None

        if extra_query:
            if 'main_filter' in extra_query and extra_query['main_filter']:
                main_filter = extra_query.pop('main_filter')

            if 'company_name' in filters and filters['company_name']:
                company_name = filters.pop('company_name')

        if g.current_user['account_type'] == ACCOUNT.ACCT_SELL_SIDE_ANALYST:
            if not account_id:
                if main_filter == RESEARCH_REPORT.MINE_COMPANY:
                    account_id = g.current_user['account_id']
                # if main_filter == RESEARCH_REPORT.MINE:
                query_filters['base'].append(
                    ResearchReport.created_by == g.current_user['row_id'])
        if g.current_user['account_type'] == ACCOUNT.ACCT_CORPORATE:
            if not corporate_account_id:
                if main_filter == RESEARCH_REPORT.MINE_COMPANY:
                    corporate_account_id = g.current_user['account_id']

        if company_name:
            query_filters['filters'].append(
                func.lower(CrossAccount.account_name).like(
                    "%" + company_name.lower() + "%"))

        query = self._build_final_query(
            query_filters, query_session, operator)

        query = query.options(
            joinedload(ResearchReport.account).
            joinedload(Account.profile),
            joinedload(ResearchReport.creator).load_only(
                'row_id', 'account_id').joinedload(
                User.account).joinedload(Account.profile))

        query = query.join(
            Account,
            Account.row_id == ResearchReport.account_id).join(
            AccountCorporate,
            AccountCorporate.row_id == ResearchReport.corporate_account_id)

        if corporate_account_id:
            query = query.filter(and_(
                ResearchReport.corporate_account_id == corporate_account_id))
        if account_id:
            query = query.filter(and_(
                ResearchReport.account_id == account_id))

        return query, db_projection, s_projection, order, paging

    # @swag_from('swagger_docs/corporate_announcement_get_list.yml')
    def get(self):
        """
        Get the list
        """
        total = 0
        research_report_read_schema = ResearchReportReadArgsSchema(strict=True)
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            research_report_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(ResearchReport),
                                 operator)
            # making a copy of the main output schema
            research_report_schema = ResearchReportSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                research_report_schema = ResearchReportSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching research reports found')

            result = research_report_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
