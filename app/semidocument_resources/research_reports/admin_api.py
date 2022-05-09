"""
API endpoints for "research reports" package.
"""

from app.resources.research_reports.schemas import (
    AdminResearchReportSchema, ResearchReportReadArgsSchema)
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy import and_, func, desc, asc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only, joinedload, aliased
from werkzeug.exceptions import Forbidden, HTTPException

from app import db, c_abort, researchreportfile
from app.auth.decorators import role_permission_required
from app.base import constants as APP
from app.base.api import AuthResource
from app.common.helpers import store_file, delete_files
from app.resources.account_managers.models import AccountManager
from app.resources.accounts.models import Account
from app.resources.roles import constants as ROLE
from app.resources.users.models import User
from app.semidocument_resources.research_reports.models import (
    ResearchReport)


class AdminResearchReportAPI(AuthResource):
    """
    For creating new research report by admin
    """
    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA])
    # @swag_from('swagger_docs/admin_research_report_schema_post.yml')
    def post(self):
        """
        Create research report by admin
        """
        # main input and output schema
        admin_research_report_schema = AdminResearchReportSchema()
        # get the json data from the request
        json_data = request.form
        if not json_data:
            c_abort(400)

        try:
            data, errors = admin_research_report_schema.load(json_data)
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
            ResearchReport.root_folder_key)
        if 'file' in request.files:
            # new file being added
            # add new file
            fpath, fname, ferrors, ftype = store_file(
                researchreportfile, request.files['file'],
                sub_folder=sub_folder, full_folder=file_full_folder,
                detect_type=True, type_only=True)
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
            db.session.commit()
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

    @role_permission_required(perms=[ROLE.EPT_AA],  roles=[
        ROLE.ERT_SU, ROLE.ERT_CA])
    # @swag_from('swagger_docs/admin_research_report_schema_put.yml')
    def put(self, row_id):
        """
        Update research report by admin
        """
        admin_research_report_schema = AdminResearchReportSchema()
        model = None
        try:
            model = ResearchReport.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Research Report id: %s'
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
            data, errors = admin_research_report_schema.load(
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
            ResearchReport.root_folder_key)
        if 'file' in request.files:
            # new file being added
            # add new file
            fpath, fname, ferrors, ftype = store_file(
                researchreportfile, request.files['file'],
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

        return {'message': 'Updated Research Report id: %s' %
                           str(row_id)}, 200

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA])
    # @swag_from('swagger_docs/admin_research_report_schema_delete.yml')
    def delete(self, row_id):
        """
        Delete a research report by admin
        """
        try:
            # first find model
            model = ResearchReport.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Research Report id: %s'
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
    # @swag_from('swagger_docs/admin_research_report_schema_get.yml')
    def get(self, row_id):
        """
        Get a research report request by id by admin
        """
        result = None
        admin_research_report_schema = AdminResearchReportSchema()
        try:
            # first find model
            model = ResearchReport.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Research Report id: %s'
                                     ' does not exist' % str(row_id))
            result = admin_research_report_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class AdminResearchReportListAPI(AuthResource):
    """
    Read API for library file lists, i.e, more than 1 library file
    """
    model_class = ResearchReport

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['account', 'creator', 'editor',
            'corporate_account']
        super(
            AdminResearchReportListAPI, self).__init__(*args, **kwargs)

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
            if 'company_name' in extra_query and extra_query['company_name']:
                query_filters['filters'].append(
                    func.lower(Account.account_name).like(
                        "%" + extra_query['company_name'].lower() + "%"))

        query = self._build_final_query(
            query_filters, query_session, operator)

        AccountCorporate = aliased(Account, name='AccountCorporate')

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
        # manager can access assigned account research report only
        if g.current_user['role']['name'] == ROLE.ERT_MNG:
            query = query.join(
                AccountManager, and_(
                    ResearchReport.account_id ==
                    AccountManager.account_id, AccountManager.manager_id ==
                    g.current_user['row_id']))

        direction = asc if sort['sort'] == 'asc' else desc
        if 'account_name' in sort['sort_by']:
            query = query.order_by(direction(Account.account_name))
        if 'corporate_account_name' in sort['sort_by']:
            query = query.order_by(direction(AccountCorporate.account_name))
        return query, db_projection, s_projection, order, paging

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    # @swag_from('swagger_docs/admin_research_report_schema_get_list.yml')
    def get(self):
        """
        Get the list by admin
        """
        # schema for reading get arguments
        research_report_read_schema = ResearchReportReadArgsSchema(
            strict=True)
        total = 0
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
            admin_research_report_schema = AdminResearchReportSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                admin_research_report_schema = AdminResearchReportSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching research reports found')
            result = admin_research_report_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
