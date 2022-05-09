"""
API endpoints for "crm contact" package.
"""
import json

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy import func, and_, or_, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only, aliased
from flasgger.utils import swag_from

from app import db, c_abort, crmcontactprofilephoto
from app.base import constants as APP
from app.base.api import AuthResource
from app.common.helpers import store_file, delete_files
from app.crm_resources.crm_contacts.models import CRMContact
from app.crm_resources.crm_contacts.schemas import (
    CRMContactSchema, CRMContactReadArgsSchema, CRMCommonConnectionSchema,
    CRMCommonConnectionReadArgsSchema,
    CRMContactFactsetFundManagementSchema)
from app.crm_resources.crm_contacts import constants as CRM
from app.crm_resources.crm_contacts.helpers import (
    add_user_for_contact, update_user_id_from_crm_file)
from app.crm_resources.crm_groups.models import CRMGroup
from app.resources.contacts.models import Contact
from app.resources.users.models import User
from app.resources.user_profiles.models import UserProfile
from app.resources.accounts.models import Account
from app.resources.accounts import constants as ACCT

from queueapp.thumbnail_tasks import convert_file_into_thumbnail


class CRMContactAPI(AuthResource):
    """
    CRUD API for managing crm contact
    """

    @swag_from('swagger_docs/crm_contact_post.yml')
    def post(self):
        """
        Create a crm contact
        """

        crm_contact_schema = CRMContactSchema()
        # get the json data from the request
        json_data = request.form.to_dict()
        if not json_data:
            c_abort(400)

        try:
            if 'industry_coverage' in json_data:
                json_data['industry_coverage'] = request.form.getlist(
                    'industry_coverage')
            if 'file_ids' in json_data:
                json_data['file_ids'] = request.form.getlist('file_ids')

            data, errors = crm_contact_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            # 1) insert contact detail in user table as a guest type if not
            # exists in user
            # 2) if contact exists in user but as a guest user so, no logic
            # perform
            # 3) if contact exists in user but as system user,
            # so we not create crm contact, just make contact with creator and
            #  crm contact exists user
            response = add_user_for_contact(data)
            if not response['user']:
                c_abort(422, errors=response['extra_message'])
            if response['is_connected']:
                c_abort(422, message="Contact is already in your connection")
            data.user_id = response['user'].row_id
            data.is_system_user = response['is_system_user']
            data.created_by = g.current_user['row_id']
            data.account_id = g.current_user['account_id']
            db.session.add(data)
            db.session.commit()

            # manage files
            if crm_contact_schema._cached_files or 'file_ids' in json_data:
                for cf in crm_contact_schema._cached_files:
                    if cf not in data.files:
                        data.files.append(cf)
                db.session.commit()

            # fund management
            if 'funds' in json_data:
                for cf in json.loads(request.form['funds']):
                    cf['crm_contact_id'] = data.row_id
                    fund_data,errors = CRMContactFactsetFundManagementSchema().load(cf)
                    if errors:
                        c_abort(422, errors=errors)
                    db.session.add(fund_data)
                db.session.commit()

            profile_data = {'files': {}}
            profile_path = None
            sub_folder = data.file_subfolder_name()
            profile_full_folder = data.full_folder_path(
                CRMContact.root_profile_photo_folder_key)
            try:
                # save files
                if 'profile_photo' in request.files:
                    profile_path, profile_name, ferrors = store_file(
                        crmcontactprofilephoto, request.files['profile_photo'],
                        sub_folder=sub_folder, full_folder=profile_full_folder,
                        not_local=True)
                    if ferrors:
                        return ferrors['message'], ferrors['code']
                    profile_data['files'][profile_name] = profile_path
                # profile photo upload
                if profile_data and profile_data['files']:
                    # parse new files
                    if profile_data['files']:
                        data.profile_photo = [
                            profile_name for profile_name
                            in profile_data['files']][0]
                db.session.commit()
            except HTTPException as e:
                raise e
            except Exception as e:
                current_app.logger.exception(e)
                abort(500)
            # generate thumbnail for profile photo
            if profile_path:
                convert_file_into_thumbnail.s(
                    True, data.row_id, APP.MOD_CRM_CONTACT_PROFILE,
                    profile_path, 'profile').delay()
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

        return {'message': 'Contact Added: %s' % str(data.row_id),
                'row_id': data.row_id,
                'extra_message': response['extra_message']}, 201

    @swag_from('swagger_docs/crm_contact_put.yml')
    def put(self, row_id):
        """
        Update a crm contact
        """

        crm_contact_schema = CRMContactSchema()
        fund_manage_schema = CRMContactFactsetFundManagementSchema()
        model = None

        try:
            model = CRMContact.query.get(row_id)
            if not model:
                c_abort(404, message='Contact id: %s does not exist' %
                                     str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                c_abort(403)
            old_email = model.email
            old_user_id = model.user_id
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        profile_data = {'files': {}}
        profile_path = None
        sub_folder = model.file_subfolder_name()
        profile_full_folder = model.full_folder_path(
            CRMContact.root_profile_photo_folder_key)

        # save files
        if 'profile_photo' in request.files:
            profile_path, profile_name, ferrors = store_file(
                crmcontactprofilephoto, request.files['profile_photo'],
                sub_folder=sub_folder, full_folder=profile_full_folder,
                not_local=True)
            if ferrors:
                return ferrors['message'], ferrors['code']
            profile_data['files'][profile_name] = profile_path

        # delete files
        if 'profile_photo' in request.form:
            profile_data['delete'] = []
            if request.form['profile_photo'] == model.profile_photo:
                profile_data['delete'].append(
                    request.form['profile_photo'])
                if profile_data['delete']:
                    # delete all mentioned files
                    ferrors = delete_files(
                        profile_data['delete'], sub_folder=sub_folder,
                        full_folder=profile_full_folder)
                    if ferrors:
                        return ferrors['message'], ferrors['code']
                    # when profile photo delete profile thumbnail also delete
                    if model.profile_thumbnail:
                        th_errors = delete_files(
                            [model.profile_thumbnail],
                            sub_folder=sub_folder,
                            full_folder=profile_full_folder,
                            is_thumbnail=True)
                        if th_errors:
                            return th_errors['message'], th_errors['code']

        try:
            json_data = request.form.to_dict()
            if 'industry_coverage' in json_data:
                json_data['industry_coverage'] = request.form.getlist(
                    'industry_coverage')
            if 'file_ids' in json_data:
                json_data['file_ids'] = request.form.getlist('file_ids')

            if (not json_data and  # <- no text data
                    not profile_data['files'] and (  # <- no profile photo upload
                    'delete' not in profile_data or  # no profile photo delete
                    not profile_data['delete'])):
                # no data of any sort
                c_abort(400)
            # validate and deserialize input
            data = None
            if json_data:
                data, errors = crm_contact_schema.load(
                    json_data, instance=model, partial=True)
                if errors:
                    c_abort(422, errors=errors)

            if not data:
                data = model
            # if update email,then change user_id reference to
            response = {'extra_message': None}
            response = add_user_for_contact(data)
            if not response:
                c_abort(422, errors=response['extra_message'])
            if old_email != data.email:
                data.user_id = response['user'].row_id
                data.is_system_user = response['is_system_user']
                # update user_id from crm file library
                update_user_id_from_crm_file(
                    old_user_id, response['user'].row_id)
            # manage file list
            if crm_contact_schema._cached_files or 'file_ids' in json_data:
                # add new ones
                for cf in crm_contact_schema._cached_files:
                    if cf not in data.files:
                        data.files.append(cf)
                # remove old ones
                for oldcf in data.files[:]:
                    if oldcf not in crm_contact_schema._cached_files:
                        data.files.remove(oldcf)
                db.session.add(data)
                db.session.commit()

            # manage event files
            if 'funds' in json_data:
                # remove old ones
                for oldcf in data.fund_management[:]:
                    db.session.delete(oldcf)

                # add new ones
                for cf in json.loads(request.form['funds']):
                    cf['crm_contact_id'] = data.row_id
                    fund_data,errors = fund_manage_schema.load(cf)
                    if errors:
                        c_abort(422, errors=errors)
                    db.session.add(fund_data)
                db.session.commit()

            # profile photo upload
            if profile_data and (
                    profile_data['files'] or 'delete' in profile_data):
                # parse new files
                if profile_data['files']:
                    data.profile_photo = [
                        profile_name for profile_name
                        in profile_data['files']][0]
                # any old files to delete
                if 'delete' in profile_data:
                    for profile_name in profile_data['delete']:
                        if profile_name == data.profile_photo:
                            data.profile_photo = None
                            data.profile_thumbnail = None
            db.session.add(data)
            db.session.commit()
            if profile_path:
                convert_file_into_thumbnail.s(
                    True, data.row_id, APP.MOD_CRM_CONTACT_PROFILE,
                    profile_path, 'profile').delay()
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

        return {'message': 'Updated contact id: %s' %
                           str(row_id),
                'extra_message': response['extra_message']}, 200

    @swag_from('swagger_docs/crm_contact_delete.yml')
    def delete(self, row_id):
        """
        Delete a contact
        """

        model = None
        try:
            # first find model
            model = CRMContact.query.get(row_id)
            if model is None:
                c_abort(404, message='Contact id: %s does not exist' %
                                     str(row_id))
            # check account membership and check user role
            if model.created_by != g.current_user['row_id']:
                c_abort(403)
            groups = CRMGroup.query.filter(
                CRMGroup.created_by == g.current_user['row_id']).all()
            for group in groups:
                if model.user in group.group_contacts:
                    group.group_contacts.remove(model.user)
                db.session.add(group)
            db.session.commit()
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

    @swag_from('swagger_docs/crm_contact_get.yml')
    def get(self, row_id):
        """
        Get a contact by id
        """

        crm_contact_schema = CRMContactSchema()

        model = None
        try:
            model = CRMContact.query.get(row_id)
            if model is None:
                c_abort(404, message='Contact id: %s does not exist' %
                                     str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                c_abort(403)
            result = crm_contact_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class CRMContactListAPI(AuthResource):
    """
    Read API for CRMContact lists, i.e, more than 1 CRM Contact
    """

    model_class = CRMContact

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['creator', 'profile_thumbnail_url']
        super(CRMContactListAPI, self).__init__(*args, **kwargs)

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

        if extra_query:
            pass

        query_filters['base'].append(
            CRMContact.created_by == g.current_user['row_id'])

        query = self._build_final_query(query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/crm_contact_get_list.yml')
    def get(self):
        """
        Get the list
        """
        crm_contact_read_schema = CRMContactReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            crm_contact_read_schema)

        try:
            # build the sql query
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(CRMContact), operator)
            # making a copy of the main output schema
            crm_contact_schema = CRMContactSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                crm_contact_schema = CRMContactSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching contact found')
            result = crm_contact_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class CRMCommonContactListAPI(AuthResource):
    """
    Read API for Common connect lists, i.e, more than 1 Contact
    """

    model_class = Contact

    def __init__(self, *args, **kwargs):
        super(CRMCommonContactListAPI, self).__init__(*args, **kwargs)

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
        # for operator filter
        if operator == 'and':
            op_fxn = and_
        elif operator == 'or':
            op_fxn = or_

        # aliased models
        user = aliased(User, name='user')
        user_profile = aliased(UserProfile, name='user_profile')
        user_account = aliased(Account, name='user_account')
        # for filter
        full_name = ""
        company_name = ""
        email = ""
        module = None
        contact_type = None
        # for common filter with connection or crm contact
        q_filter = []
        if extra_query:
            if 'full_name' in extra_query and extra_query['full_name']:
                full_name = '%' + extra_query['full_name'].lower() + '%'
                q_filter.append(func.concat(func.lower(
                    user_profile.first_name), ' ', func.lower(
                    user_profile.last_name)).ilike(full_name))
            if 'module' in extra_query and extra_query['module']:
                module = extra_query['module']
            if 'company_name' in extra_query and extra_query['company_name']:
                company_name = '%' + extra_query['company_name'].lower() + '%'
                q_filter.append(
                    func.lower(user_account.account_name).ilike(
                        company_name))
            if 'email' in extra_query and extra_query['email']:
                email = '%' + extra_query['email'].lower() + '%'
                q_filter.append(func.lower(user.email).like(email))
            if 'contact_type' in extra_query and extra_query['contact_type']:
                contact_type = extra_query['contact_type']
            if 'designation' in extra_query and extra_query['designation']:
                designation = '%' + extra_query['designation'].lower() + '%'
                q_filter.append(
                    func.lower(user_profile.designation).like(designation))

        contact_query = None
        crm_contact_query = None
        final_query = None
        # build query for connection of current user
        # only for connection type contact
        if module != CRM.CONTACT:
            contact_sent_by_query = db.session.query(
                user, Contact.row_id.label('contact_id'),
                func.concat(CRM.CONNECTION).label('module'),
                user.account_type.label('contact_type'),
                user_account.account_name.label('company_name')).join(
                Contact, user.row_id == Contact.sent_to).join(
                user_account, user_account.row_id == user.account_id).filter(
                Contact.sent_by == g.current_user['row_id'],
                user.deactivated.is_(False))
            # for sent to query
            contact_sent_to_query = db.session.query(
                user, Contact.row_id.label('contact_id'),
                func.concat(CRM.CONNECTION).label('module'),
                user.account_type.label('contact_type'),
                user_account.account_name.label('company_name')).join(
                Contact, user.row_id == Contact.sent_by).join(
                user_account, user_account.row_id == user.account_id).filter(
                Contact.sent_to == g.current_user['row_id'],
                user.deactivated.is_(False))
            # union with sent by and sent to query
            contact_query = contact_sent_by_query.union(
                contact_sent_to_query)
            if contact_type:
                contact_query = contact_query.filter(
                    user.account_type == contact_type)
            final_query = contact_query
        # only for crm contact type contact
        if module != CRM.CONNECTION:
            # bulid query for CRMContact
            crm_contact_query = db.session.query(
                user, CRMContact.row_id.label('contact_id'),
                func.concat(CRM.CONTACT).label('module'),
                CRMContact.contact_type.label('contact_type'),
                CRMContact.company.label('company_name')).join(
                CRMContact, user.row_id == CRMContact.user_id).filter(and_(
                    CRMContact.created_by == g.current_user['row_id']))
            if contact_type:
                crm_contact_query = crm_contact_query.filter(
                    CRMContact.contact_type == contact_type)
            final_query = crm_contact_query
            if company_name:
                q_filter.append(func.lower(CRMContact.company).ilike(
                    company_name))
        # if user want to fetch all contact connection and crm contact
        if module == CRM.ALL or not module:
            final_query = contact_query.union(crm_contact_query)

        final_query = final_query.join(
                user_profile, user.row_id == user_profile.user_id).join(
                user_account, user.account_id == user_account.row_id).filter(
                op_fxn(*q_filter),
                user_profile.account_type.notin_(
                    (ACCT.ACCT_SME, ACCT.ACCT_PRIVATE)
                    ), user_account.blocked==False)
        # sort in desc or asc
        if sort:
            if sort['sort'] == 'dsc':
                final_query = final_query.order_by(desc(func.concat(
                    user_profile.first_name, ' ', user_profile.last_name)))
            else:
                final_query = final_query.order_by(func.concat(
                    user_profile.first_name, ' ', user_profile.last_name))
        order = []
        return final_query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/crm_common_contact_get_list.yml')
    def get(self):
        """
        Get common connection
        """

        crm_common_read_schema = CRMCommonConnectionReadArgsSchema(strict=True)

        filters, pfields, sort, pagination, operator = self.parse_args(
            crm_common_read_schema)

        try:
            # build the sql query
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Contact), operator)
            # making a copy of the main output schema
            crm_common_schema = CRMCommonConnectionSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                crm_common_schema = CRMCommonConnectionSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching contacts found')
            result = crm_common_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class CRMContactBulkDeletAPI(AuthResource):
    """
    For Delete bulk CRM contacts

    """

    def put(self):

        model = None

        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)
        if not json_data["ids"]:
            c_abort(422,message='Contacts not exist')
        contacts_list = json_data["ids"]
        try:
            groups = CRMGroup.query.filter(
                CRMGroup.created_by == g.current_user['row_id']).all()
            for contact_id in contacts_list:
                # first find model
                model = CRMContact.query.get(contact_id)
                if model is None:
                    c_abort(404, message='CRMContact id: %s'
                            ' does not exist' % str(contact_id))
                if model.created_by != g.current_user['row_id']:
                    c_abort(403)
                for group in groups:
                    if model.user in group.group_contacts:
                        group.group_contacts.remove(model.user)
                    db.session.add(group)
                db.session.commit()
                # if model is found, and not yet deleted, delete it
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
        return {'message': 'CRMContact are Deleted'}, 200