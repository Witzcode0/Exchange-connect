"""
API endpoints for "crm group" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only, joinedload
from flasgger.utils import swag_from

from app import db, c_abort, crmgroupicon
from app.base import constants as APP
from app.resources.users import constants as USER
from app.base.api import AuthResource
from app.common.helpers import store_file, delete_files
from app.crm_resources.crm_groups.models import CRMGroup
from app.crm_resources.crm_groups.schemas import (
    CRMGroupSchema, CRMGroupReadArgsSchema, BulkGroupContactSchema)
from app.crm_resources.crm_contacts.schemas import CRMContactSchema
from app.crm_resources.crm_contacts.models import CRMContact
from app.crm_resources.crm_contacts.helpers import add_user_for_contact
from queueapp.notification_tasks import add_contact_request_notification
from queueapp.user_stats_tasks import manage_users_stats


class CRMGroupAPI(AuthResource):
    """
    CRUD API for managing crm group
    """

    @swag_from('swagger_docs/crm_group_post.yml')
    def post(self):
        """
        Create a crm group
        """
        crm_group_schema = CRMGroupSchema()
        # get the json data from the request
        json_data = request.form.to_dict()
        if not json_data:
            c_abort(400)

        try:
            if 'contact_ids' in json_data:
                json_data['contact_ids'] = request.form.getlist(
                    'contact_ids')

            data, errors = crm_group_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            data.created_by = g.current_user['row_id']
            data.account_id = g.current_user['account_id']
            db.session.add(data)
            db.session.commit()

            # manage contacts
            if crm_group_schema._cached_contact or 'contact_ids' in json_data:
                for cf in crm_group_schema._cached_contact:
                    if cf not in data.group_contacts:
                        data.group_contacts.append(cf)
                db.session.commit()

            icon_data = {'files': {}}
            sub_folder = data.file_subfolder_name()
            icon_full_folder = data.full_folder_path(
                CRMGroup.root_icon_folder_key)
            try:
                # save files
                if 'group_icon' in request.files:
                    icon_path, icon_name, ferrors = store_file(
                        crmgroupicon, request.files['group_icon'],
                        sub_folder=sub_folder, full_folder=icon_full_folder,
                        not_local=True)
                    if ferrors:
                        return ferrors['message'], ferrors['code']
                    icon_data['files'][icon_name] = icon_path
                # icon photo upload
                if icon_data and icon_data['files']:
                    # parse new files
                    if icon_data['files']:
                        data.group_icon = [
                            icon_name for icon_name
                            in icon_data['files']][0]
                db.session.commit()
            except HTTPException as e:
                raise e
            except Exception as e:
                current_app.logger.exception(e)
                abort(500)
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (created_by, email)=(example@example.com) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Group created: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @swag_from('swagger_docs/crm_group_put.yml')
    def put(self, row_id):
        """
        Update a crm group
        """

        crm_group_schema = CRMGroupSchema()
        model = None

        try:
            model = CRMGroup.query.get(row_id)
            if not model:
                c_abort(404, message='Group id: %s does not exist' %
                                     str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                c_abort(403)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        icon_data = {'files': {}}
        sub_folder = model.file_subfolder_name()
        icon_full_folder = model.full_folder_path(
            CRMGroup.root_icon_folder_key)

        # save files
        if 'group_icon' in request.files:
            icon_path, icon_name, ferrors = store_file(
                crmgroupicon, request.files['group_icon'],
                sub_folder=sub_folder, full_folder=icon_full_folder,
                not_local=True)
            if ferrors:
                return ferrors['message'], ferrors['code']
            icon_data['files'][icon_name] = icon_path

        # delete files
        if 'group_icon' in request.form:
            icon_data['delete'] = []
            if request.form['group_icon'] == model.group_icon:
                icon_data['delete'].append(
                    request.form['group_icon'])
                if icon_data['delete']:
                    # delete all mentioned files
                    ferrors = delete_files(
                        icon_data['delete'], sub_folder=sub_folder,
                        full_folder=icon_full_folder)
                    if ferrors:
                        return ferrors['message'], ferrors['code']

        try:
            json_data = request.form.to_dict()
            if 'contact_ids' in json_data:
                json_data['contact_ids'] = request.form.getlist(
                    'contact_ids')
            data, errors = crm_group_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)

            if not data:
                data = model

            # manage file list
            if crm_group_schema._cached_contact or 'contact_ids' in json_data:
                # add new ones
                for cf in crm_group_schema._cached_contact:
                    if cf not in data.group_contacts:
                        data.group_contacts.append(cf)
                # remove old ones
                for oldcf in data.group_contacts[:]:
                    if oldcf not in crm_group_schema._cached_contact:
                        data.group_contacts.remove(oldcf)
                db.session.add(data)
                db.session.commit()

            # icon photo upload
            if icon_data and icon_data['files']:
                # parse new files
                if 'files' in icon_data and icon_data['files']:
                    data.group_icon = [
                        icon_name for icon_name
                        in icon_data['files']][0]
                # any old files to delete
                if 'delete' in icon_data and icon_data['delete']:
                    for profile_name in icon_data['delete']:
                        if profile_name == data.icon_name:
                            data.group_icon = None
                db.session.add(data)
                db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (name)=(example@example.com) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Updated group id: %s' %
                           str(row_id)}, 200

    @swag_from('swagger_docs/crm_group_delete.yml')
    def delete(self, row_id):
        """
        Delete a group
        """

        model = None
        try:
            # first find model
            model = CRMGroup.query.get(row_id)
            if model is None:
                c_abort(404, message='Group id: %s does not exist' %
                                     str(row_id))
            # check account membership and check user role
            if model.created_by != g.current_user['row_id']:
                c_abort(403)

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

    @swag_from('swagger_docs/crm_group_get.yml')
    def get(self, row_id):
        """
        Get a group by id
        """

        crm_group_schema = CRMGroupSchema()

        model = None
        try:
            model = CRMGroup.query.get(row_id)
            if model is None:
                c_abort(404, message='Group id: %s does not exist' %
                                     str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                c_abort(403)
            result = crm_group_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data}, 200


class CRMGroupListAPI(AuthResource):
    """
    Read API for CRM Group lists, i.e, more than 1 group
    """

    model_class = CRMGroup

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['group_icon_url', 'group_crm_connections', 'group_crm_contacts', 'group_contacts']
        super(CRMGroupListAPI, self).__init__(*args, **kwargs)

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
        # build specific extra queries filters
        if extra_query:
            pass

        query_filters['base'].append(
            CRMGroup.created_by == g.current_user['row_id'])
        query = self._build_final_query(query_filters, query_session, operator)

        query = query.options(joinedload(CRMGroup.account))

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/crm_group_get_list.yml')
    def get(self):
        """
        Get the list
        """
        # schema for reading get arguments
        crm_group_read_schema = CRMGroupReadArgsSchema(
            strict=True)

        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            crm_group_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(CRMGroup), operator)
            # making a copy of the main output schema
            crm_group_schema = CRMGroupSchema()
            print('db_projection: ', db_projection)
            print('s_projection: ', s_projection)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                crm_group_schema = CRMGroupSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching group found')
            result = crm_group_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class BulkGroupContactAPI(AuthResource):
    """
    Create contact in bulk and in group
    """

    def post(self):
        """
        Create contacts group in bulk
        :return:
        """
        response = None
        crm_group_schema = CRMGroupSchema()
        crm_contact_schema = CRMContactSchema()
        group_data = None
        contact_users = []
        json_data = request.get_json()
        contact_req_ids = []
        notification_types = []
        stats_user_ids = []
        if not json_data:
            c_abort(400)

        try:
            data, errors = BulkGroupContactSchema().load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # first create or update group
            if 'group' in data and data['group']:
                # if group is exists
                if 'row_id' in data['group'] and data['group']['row_id']:
                    group_model = CRMGroup.query.get(data['group']['row_id'])
                    if not group_model:
                        c_abort(404, message='Group id: %s does not exist' %
                                             str(data['group']['row_id']))
                    # check ownership
                    if group_model.created_by != g.current_user['row_id']:
                        c_abort(403)
                    # changes of group
                    group_data, errors = crm_group_schema.load(
                        data['group'], instance=group_model, partial=True)
                    if errors:
                        c_abort(422, errors=errors)
                # new group creation
                elif 'group' in data and data['group']:
                    group_data, errors = crm_group_schema.load(data['group'])
                    if errors:
                        c_abort(422, errors=errors)
                    group_data.created_by = g.current_user['row_id']
                    group_data.account_id = g.current_user['account_id']
                    db.session.add(group_data)
                    db.session.commit()
                # manage contacts
                if (crm_group_schema._cached_contact or
                            'contact_ids' in data['group']):
                    for cf in crm_group_schema._cached_contact:
                        if cf not in group_data.group_contacts:
                            group_data.group_contacts.append(cf)
                        # remove old ones
                        for oldcf in group_data.group_contacts[:]:
                            if oldcf not in crm_group_schema._cached_contact:
                                group_data.group_contacts.remove(oldcf)
                    db.session.commit()
                response = {'message': 'All Contact Added in group: %s' % str(
                    group_data.row_id), 'row_id': group_data.row_id}
            # first all contact should be create
            if 'excel_contacts' in data and data['excel_contacts']:
                for contact in data['excel_contacts']:
                    # first create contact as user
                    response = add_user_for_contact(contact)
                    if not response['user']:
                        c_abort(422, errors=response['extra_message'])
                    # for adding in group contact
                    contact_users.append(response['user'])
                    if response['is_connected'] :
                        continue
                    crm_contact = CRMContact.query.filter(and_(
                            CRMContact.email == contact.email,
                            CRMContact.created_by == g.current_user['row_id'])
                            ).first()
                    if crm_contact:
                        # if contact is already exists for current user update
                        contact, error = crm_contact_schema.load(
                            contact.__dict__, instance=crm_contact)

                    contact.user_id = response['user'].row_id
                    contact.is_system_user = response['is_system_user']
                    contact.created_by = g.current_user['row_id']
                    contact.account_id = g.current_user['account_id']
                    db.session.add(contact)
                    db.session.commit()
                    if response['contact_req']:
                        contact_req_ids.append(
                            response['contact_req']['row_id']
                        )
                        notification_types.append(
                            response['contact_req']['noti_type']
                        )
                        if 'user_ids' in response['contact_req']:
                            stats_user_ids.extend(
                                response['contact_req']['user_ids']
                            )

                response = {'message': 'All Contact Added'}

            # adding created contact in existing group
            if contact_users and group_data:
                for cu in contact_users:
                    if cu not in group_data.group_contacts:
                        group_data.group_contacts.append(cu)
                    db.session.add(cu)
                db.session.commit()
                response = {'message': 'All Contact Added in group: %s' % str(
                    group_data.row_id), 'row_id': group_data.row_id}
            if contact_req_ids:
                add_contact_request_notification.s(
                    True, contact_req_ids, notification_types).delay()
            if stats_user_ids:
                # update user total_contact
                # for sent_to and send_by user
                manage_users_stats.s(
                    True, stats_user_ids, USER.USR_CONTS).delay()

        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return response, 201
