"""
API endpoints for "helptickets" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from flasgger.utils import swag_from

from app import db, c_abort, hticketattachment
from app.base.api import AuthResource
from app.base import constants as APP
from app.common.helpers import store_file, delete_files
from app.resources.roles import constants as ROLE
from app.helpdesk_resources.help_tickets.models import HelpTicket
from app.helpdesk_resources.help_tickets.schemas import (
    HelpTicketSchema, HelpTicketReadArgsSchema)
from app.resources.users.models import User
from app.resources.account_managers.models import AccountManager
from app.domain_resources.domains.helpers import (
    get_domain_info, get_domain_name)

from queueapp.helpdesk_tasks import send_helpdesk_email


class HelpTicketAPI(AuthResource):
    """
    CRUD API for help tickets
    """

    @swag_from('swagger_docs/help_tickets_post.yml')
    def post(self):
        """
        Create a ticket
        """
        # main input and output schema
        help_ticket_schema = HelpTicketSchema()
        # get the json data from the request
        json_data = request.form
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = help_ticket_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            domain_id, domain_config = get_domain_info(get_domain_name())
            data.domain_id = domain_id
            db.session.add(data)
            db.session.commit()
            # send email
            send_helpdesk_email.s(True, data.row_id).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (assignee_id)=(17) is not present in table "user"
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

        file_data = {'files': {}}
        sub_folder = data.file_subfolder_name()
        attachment_full_folder = data.full_folder_path(
            HelpTicket.root_folder_key)

        if 'attachment' in request.files:
            # new file being added
            # add new file
            fpath, fname, ferrors, ftype = store_file(
                hticketattachment, request.files['attachment'],
                sub_folder=sub_folder, full_folder=attachment_full_folder,
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
                    data.attachment = [
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

        return {'message': 'Help Ticket Added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @swag_from('swagger_docs/help_tickets_put.yml')
    def put(self, row_id):
        """
        Update a help ticket, either pass file data as multipart-form,
        or json data
        """
        # main input and output schema
        help_ticket_schema = HelpTicketSchema()
        # first find model
        model = None
        try:
            model = HelpTicket.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Help Ticket id:'
                        '%s does not exist' % str(row_id))
            # check ownership
            if (model.created_by != g.current_user['row_id'] and
                    g.current_user['role']['name'] not in [
                        ROLE.ERT_SU, ROLE.ERT_AD]):
                abort(403)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            abort(500)

        # get the json data from the request
        json_data = request.form
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input
            data, errors = help_ticket_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            data.updated_by = g.current_user['row_id']
            # no errors, so update data to db
            db.session.add(data)
            db.session.commit()

        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (assignee_id)=(17) is not present in table "user"
                column = e.orig.diag.message_detail.split('(')[1][:-2]
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

        file_data = {'files': {}}
        sub_folder = data.file_subfolder_name()
        attachment_full_folder = data.full_folder_path(
            HelpTicket.root_folder_key)

        if 'attachment' in request.files:
            # new file being added
            # add new file
            fpath, fname, ferrors, ftype = store_file(
                hticketattachment, request.files['attachment'],
                sub_folder=sub_folder,
                full_folder=attachment_full_folder,
                detect_type=True, type_only=True, not_local=True)
            if ferrors:
                db.session.delete(data)
                db.session.commit()
                return ferrors['message'], ferrors['code']
            file_data['files'][fname] = fpath
        # delete files
        if 'attachment' in request.form:
            file_data['delete'] = []
            if request.form['attachment'] == data.attachment:
                file_data['delete'].append(
                    request.form['attachment'])
                if file_data['delete']:
                    # delete all mentioned files
                    ferrors = delete_files(
                        file_data['delete'], sub_folder=sub_folder,
                        full_folder=attachment_full_folder)
                    if ferrors:
                        return ferrors['message'], ferrors['code']

        try:
            if file_data and (file_data['files'] or 'delete' in file_data):
                # populate db data from file_data
                # parse new files
                if file_data['files']:
                    data.attachment = [
                        fname for fname in file_data['files']][0]

                # any old files to delete
                if 'delete' in file_data:
                    for attachment in file_data['delete']:
                        if attachment == data.attachment:
                            data.attachment = None

            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Updated Help Ticket id: %s' % str(row_id)}, 200

    @swag_from('swagger_docs/help_tickets_delete.yml')
    def delete(self, row_id):
        """
        Delete a help ticket
        """
        model = None
        try:
            # first find model
            model = HelpTicket.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Help Ticket id: %s does'
                        ' not exist' % str(row_id))
            # check ownership
            if (model.created_by != g.current_user['row_id'] and
                    g.current_user['role']['name'] not in [
                        ROLE.ERT_SU, ROLE.ERT_AD]):
                abort(403)
            # if model is found, and not yet deleted, delete it
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

    @swag_from('swagger_docs/help_tickets_get.yml')
    def get(self, row_id):
        """
        Get a help ticket by id
        """
        # main input and output schema
        help_ticket_schema = HelpTicketSchema()
        model = None
        try:
            # first find model
            model = HelpTicket.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Help Ticket id: %s'
                        ' does not exist' % str(row_id))
            # check ownership
            if (model.created_by != g.current_user['row_id'] and
                    g.current_user['role']['name'] not in [
                        ROLE.ERT_SU, ROLE.ERT_AD, ROLE.ERT_MNG]):
                abort(403)
            result = help_ticket_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class HelpTicketListAPI(AuthResource):
    """
    Read API for help ticket lists, i.e, more than 1 help ticket
    """
    model_class = HelpTicket

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['all_comments']
        super(HelpTicketListAPI, self).__init__(*args, **kwargs)

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

        if g.current_user['role']['name'] not in [
                ROLE.ERT_SU, ROLE.ERT_AD, ROLE.ERT_MNG]:
            query_filters['base'].append(
                HelpTicket.created_by == g.current_user['row_id'])

        query = self._build_final_query(query_filters, query_session, operator)
        # manager can access assigned account tickets only
        if g.current_user['role']['name'] == ROLE.ERT_MNG:
            query = query.join(
                User, User.row_id == HelpTicket.created_by).join(
                AccountManager, and_(
                    AccountManager.account_id == User.account_id,
                    AccountManager.manager_id == g.current_user['row_id']))
        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/help_tickets_get_list.yml')
    def get(self):
        """
        Get the list
        """
        # schema for reading get arguments
        help_ticket_read_schema = HelpTicketReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            help_ticket_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(HelpTicket), operator)
            # making a copy of the main output schema
            help_ticket_schema = HelpTicketSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                help_ticket_schema = HelpTicketSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                return {'message': 'No matching help tickets found'}, 404
            result = help_ticket_schema.dump(models, many=True)
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
