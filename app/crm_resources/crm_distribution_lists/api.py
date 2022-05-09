"""
API endpoints for "crm distribution list" package.
"""

import json

from werkzeug.exceptions import Forbidden, HTTPException
from sqlalchemy.exc import IntegrityError
from flask import request, current_app, g
from webargs.flaskparser import parser
from flask_restful import abort
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import load_only, joinedload
from flasgger import swag_from

from app import db, c_abort, crmdistlistattach
from app.base.api import AuthResource
from app.base.schemas import BaseCommonSchema
from app.base import constants as APP
from app.common.helpers import store_file, delete_files
from app.crm_resources.crm_distribution_lists.models import CRMDistributionList
from app.crm_resources.crm_distribution_lists.schemas import (
    CRMDistributionListSchema, CRMDistributionListReadArgsSchema,
    CRMDistributionGetListSchema)
from app.crm_resources.crm_distribution_invitee_lists.models import (
    CRMDistributionInviteeList)
from app.crm_resources.crm_distribution_invitee_lists.schemas import (
    CRMDistributionInviteeListSchema)
from app.resources.user_dashboard.schemas import (
    UserEventMonthWiseStatsSchema)
from app.base.schemas import BaseReadArgsSchema

from queueapp.crm_distribution_lists.email_tasks import (
    send_distribution_invitee_list_email)


class CRMDistributionAPI(AuthResource):
    """
    For creating new crm distribution list
    """
    @swag_from('swagger_docs/crm_distribution_list_post.yml')
    def post(self):
        """
        Create crm distribution list
        :return:
        """

        crm_distribution_schema = CRMDistributionListSchema()
        # get the form data from the request
        input_data = None
        input_data = parser.parse(
            BaseCommonSchema(), locations=('querystring',))
        json_data = request.form.to_dict()
        if not json_data:
            c_abort(400)

        try:
            if 'attachments' in json_data:
                json_data.pop('attachments')
            if 'crm_distribution_invitees' in json_data:
                json_data['crm_distribution_invitees'] = json.loads(
                    request.form['crm_distribution_invitees'])
            if 'html_file_ids' in json_data:
                json_data['html_file_ids'] = request.form.getlist(
                    'html_file_ids')
            data, errors = crm_distribution_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.account_id = g.current_user['account_id']
            data.updated_by = data.created_by

            if data.crm_distribution_invitees:
                for invitee in data.crm_distribution_invitees:
                    invitee.created_by = g.current_user['row_id']
                    invitee.updated_by = g.current_user['row_id']
            if 'launch' in input_data and input_data['launch']:
                data.is_draft = False
            db.session.add(data)
            db.session.commit()
            # manage files list
            if crm_distribution_schema._cached_files:
                for cf in crm_distribution_schema._cached_files:
                    if cf not in data.html_files:
                        data.html_files.append(cf)
            db.session.add(data)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (corporate_access_event_id, participant_email)=(
                # 193, tes@gmail.com) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
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
        file_full_folder = data.full_folder_path(
            CRMDistributionList.root_attachment_folder_key)

        if 'attachments' in request.files:
            # new file being added
            # add new file
            attach_files = request.files.getlist('attachments')
            # remove duplicate files
            request_files = [i for n, i in enumerate(attach_files)
                             if i not in attach_files[n + 1:]]
            for files in request_files:
                fpath, fname, ferrors, ftype = store_file(
                    crmdistlistattach, files,
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
                    data.attachments = [
                        fname for fname in file_data['files']]

            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
            if data.is_draft is False:
                send_distribution_invitee_list_email.s(
                    True, data.row_id).delay()
        except HTTPException as e:
            db.session.rollback()
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Distribution List created: %s' %
                           str(data.row_id), 'row_id': data.row_id}, 201

    @swag_from('swagger_docs/crm_distribution_list_put.yml')
    def put(self, row_id):
        """
        Update crm distribution list
        :return:
        """
        crm_distribution_schema = CRMDistributionListSchema()
        invitee_schema = CRMDistributionInviteeListSchema()
        model = None
        input_data = None
        input_data = parser.parse(
            BaseCommonSchema(), locations=('querystring',))
        try:
            model = CRMDistributionList.query.get(row_id)
            if model is None:
                c_abort(404, message='Distribution List id: %s'
                                     ' does not exist' % str(row_id))
            # ownership check
            if model.created_by != g.current_user['row_id']:
                abort(403)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        file_data = {'files': {}}
        sub_folder = model.file_subfolder_name()
        file_full_folder = model.full_folder_path(
            CRMDistributionList.root_attachment_folder_key)
        if 'attachments' in request.files:
            # new file being added
            # add new file
            attach_files = request.files.getlist('attachments')
            # remove duplicate files
            request_files = [i for n, i in enumerate(attach_files)
                             if i not in attach_files[n + 1:]]
            for files in request_files:
                if model.attachments and files.filename in model.attachments:
                    continue
                fpath, fname, ferrors, ftype = store_file(
                    crmdistlistattach, files,
                    sub_folder=sub_folder, full_folder=file_full_folder,
                    detect_type=True, type_only=True)
                if ferrors:
                    return ferrors['message'], ferrors['code']
                file_data['files'][fname] = fpath

        # delete files
        if 'attachments' in request.form:
            file_data['delete'] = []
            for file_name in request.form.getlist('attachments'):
                if model.attachments and file_name in model.attachments:
                    file_data['delete'].append(file_name)
            if file_data['delete']:
                # delete all mentioned files
                ferrors = delete_files(
                    file_data['delete'], sub_folder=sub_folder,
                    full_folder=file_full_folder)
                if ferrors:
                    return ferrors['message'], ferrors['code']

        # get the json data from the request
        json_data = request.form.to_dict()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input
            crm_distribution_invitees = []
            if 'attachments' in json_data:
                json_data.pop('attachments')
            if 'crm_distribution_invitees' in json_data:
                json_data.pop('crm_distribution_invitees')
                crm_distribution_invitees = json.loads(
                    request.form['crm_distribution_invitees'])
            if 'html_file_ids' in json_data:
                json_data['html_file_ids'] = request.form.getlist(
                    'html_file_ids')
            data, errors = crm_distribution_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            # no errors, so update data to db
            if 'launch' in input_data and input_data['launch']:
                data.is_draft = False
            db.session.add(data)
            db.session.commit()
            # update and insert invitees
            invitee_emails = []
            if crm_distribution_invitees:
                for invitee in crm_distribution_invitees:
                    if 'row_id' in invitee:
                        invitee_model = CRMDistributionInviteeList.query.filter(
                            CRMDistributionInviteeList.row_id == invitee[
                                'row_id']).first()
                        if not invitee_model:
                            continue

                        invitee_data, errors = invitee_schema.load(
                            invitee, instance=invitee_model, partial=True)
                        if errors:
                            c_abort(422, errors=errors)
                        invitee_data.updated_by = g.current_user['row_id']
                        db.session.add(invitee_data)
                        invitee_emails.append(invitee_data.invitee_email)
                    else:
                        invitee['distribution_list_id'] = row_id
                        invitee_data, errors = invitee_schema.load(invitee)
                        if errors:
                            c_abort(422, errors=errors)
                        invitee_model = None
                        invitee_model = CRMDistributionInviteeList.query.filter(
                            and_(CRMDistributionInviteeList.invitee_email ==
                                 invitee_data.invitee_email,
                                 CRMDistributionInviteeList.
                                 distribution_list_id == row_id)).first()
                        if invitee_model:
                            invitee_emails.append(invitee_data.invitee_email)
                            continue
                        invitee_data.created_by = g.current_user['row_id']
                        invitee_data.updated_by = g.current_user['row_id']
                        db.session.add(invitee_data)
                        invitee_emails.append(invitee_data.invitee_email)
                db.session.commit()

            if file_data and (file_data['files'] or 'delete' in file_data):
                # populate db data from file_data
                # parse new files
                attachment_files = []
                if data.attachments:
                    attachment_files = data.attachments[:]
                if file_data['files']:
                    attachment_files.extend([
                        fname for fname in file_data['files']])
                    # data.attachments = attachment_files
                # any old files to delete
                if 'delete' in file_data:
                    for file in file_data['delete']:
                        if file in attachment_files:
                            attachment_files.remove(file)
                data.attachments = attachment_files
            # manage file list
            if (crm_distribution_schema._cached_files or
                        'html_file_ids' in json_data):
                # add new ones
                for cf in crm_distribution_schema._cached_files:
                    if cf not in data.html_files:
                        data.html_files.append(cf)
                # remove old ones
                for oldcf in data.html_files[:]:
                    if oldcf not in crm_distribution_schema._cached_files:
                        data.html_files.remove(oldcf)
                db.session.add(data)
                db.session.commit()
            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
            # delete old invitee which are not send by user in invitee list
            # only not send at email type invitee will be delete
            if invitee_emails:
                CRMDistributionInviteeList.query.filter(and_(
                    CRMDistributionInviteeList.distribution_list_id == row_id,
                    CRMDistributionInviteeList.is_mail_sent.is_(False),
                    CRMDistributionInviteeList.invitee_email.notin_(
                        invitee_emails))).delete(synchronize_session=False)
                db.session.commit()
            if data.is_draft is False:
                send_distribution_invitee_list_email.s(
                    True, row_id).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (corporate_access_event_id, participant_email)=(
                # 193, tes@gmail.com) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            db.session.rollback()
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Updated Distribution List id: %s' %
                           str(row_id)}, 200

    def delete(self, row_id):
        """
        Delete a Corporate Access Event
        """
        model = None
        try:
            # first find model
            model = CRMDistributionList.query.get(row_id)
            if model is None:
                c_abort(404, message='Distribution List '
                        'id: %s does not exist' % str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            if model.is_draft is False:
                c_abort(422, message='Distribution List published,'
                        ' so it cannot be deleted')
            db.session.delete(model)
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

    @swag_from('swagger_docs/crm_distribution_list_get.yml')
    def get(self, row_id):
        """
        Get a Distribution list request by id
        """
        model = None
        try:
            # first find model
            model = CRMDistributionList.query.get(row_id)
            if model is None:
                c_abort(404, message='Distribution list id: %s'
                                     ' does not exist' % str(row_id))
            result = CRMDistributionListSchema().dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class CRMDistributionListAPI(AuthResource):
    """
    Read API for Corporate Access Event lists, i.e, more than 1
    """
    model_class = CRMDistributionList

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['creator', 'attachment_urls']
        super(CRMDistributionListAPI, self).__init__(*args, **kwargs)

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

        query_filters['base'].append(
            CRMDistributionList.created_by == g.current_user['row_id'])

        query = self._build_final_query(
            query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/crm_distribution_list_get_list.yml')
    def get(self):
        """
        Get the list
        """

        models = []
        total = 0
        crm_distribution_read_schema = CRMDistributionListReadArgsSchema(
            strict=True)
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            crm_distribution_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(CRMDistributionList),
                                 operator)
            crm_distribution_schema = CRMDistributionGetListSchema(
                exclude=CRMDistributionListSchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                crm_distribution_schema = CRMDistributionGetListSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching distribution list found')
            result = crm_distribution_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data, 'total': total}, 200

class UserDistListMonthWiseStatsAPI(AuthResource):
    """
    Get API for managing user distribution list wise stats
    """
    model_class = CRMDistributionList

    def __init__(self, *args, **kwargs):
        super(UserDistListMonthWiseStatsAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """

        query_filters, extra_query, db_projection, s_projection, order, \
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)

        query_filters_union = {}
        query_filters_union['base'] = query_filters['base'][:]
        query_filters_union['filters'] = query_filters['filters'][:]
        query_filters_union['base'].append(
            CRMDistributionList.created_by == g.current_user['row_id'])

        query_for_union = self._build_final_query(
            query_filters_union, query_session, operator)
        dl_sub_query = query_for_union.subquery()
        month_query = db.session.query(
            func.generate_series(1, 12, 1).label('month')).subquery()
        dl_month_wise_query = db.session.query(
            month_query.c.month.label(
                'month'), func.count(dl_sub_query.c.id).label(
                'count')).join(
            dl_sub_query, month_query.c.month == func.extract(
                'month', dl_sub_query.c.created_date), isouter=True).group_by(
            month_query.c.month).order_by(month_query.c.month)
        return dl_month_wise_query

    def get(self):
        """
        Get user dashboard stats
        """

        base_read_schema = BaseReadArgsSchema()
        filters, pfields, sort, pagination, operator = self.parse_args(
            base_read_schema)
        try:
            # build the sql query
            dl_month_wise_query = self.build_query(
                filters, pfields, sort, pagination, db.session.query(
                    CRMDistributionList), operator)
            contact_counts = dl_month_wise_query.all()
            result = UserEventMonthWiseStatsSchema().dump(
                contact_counts, many=True)
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'result': result.data}, 200