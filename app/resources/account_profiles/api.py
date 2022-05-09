"""
API endpoints for "account profiles" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g, json
from flask_restful import abort
from sqlalchemy import and_, func, or_, any_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import load_only, joinedload, contains_eager, Load
from flasgger.utils import swag_from

from app import db, c_abort, acctprofilephoto, acctcoverphoto
from app.base.api import AuthResource, BaseResource
from app.common.helpers import store_file, delete_files
from app.resources.account_profiles.models import AccountProfile
from app.resources.account_profiles.schemas import (
    AccountProfileSchema, AccountProfileReadArgsSchema,
    AccountProfileListSchema, AccountProfileTeamReadArgsSchema)
from app.resources.accounts import constants as ACCOUNT
from app.resources.follows.models import CFollow
from app.resources.accounts.models import Account
from app.resources.roles import constants as ROLE
from app.base import constants as APP
from app.resources.user_profiles.schemas import UserProfileSchema
from app.resources.user_profiles.models import UserProfile
from app.resources.users.models import User
from app.resources.contacts.models import Contact
from app.resources.contact_requests.models import ContactRequest
from app.resources.contact_requests import constants as CONREQUEST

from app.resources.designations.models import Designation

from queueapp.thumbnail_tasks import convert_file_into_thumbnail


class AccountProfileAPI(AuthResource):
    """
    CRUD API for account profile
    """

    @swag_from('swagger_docs/account_profile_put.yml')
    def put(self, account_id):
        """
        Update an account profile, either pass file data as multipart-form,
        or json data
        """
        account_profile_schema = AccountProfileSchema()
        model = None
        try:
            model = AccountProfile.query.options(joinedload(
                AccountProfile.account)).filter_by(
                account_id=account_id).first()
            if model is None or model.deleted:
                c_abort(404, message='Account Profile id: %s does not exist' %
                                     str(g.current_user['account_id']))

            if (model.account_id != g.current_user['account_id'] and
                    ROLE.EPT_AA not in g.current_user['role']['permissions']):
                c_abort(403)

        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        profile_data = {'files': {}}
        cover_data = {'files': {}}
        profile_path = None
        cover_path = None
        sub_folder = model.file_subfolder_name()
        profile_full_folder = model.full_folder_path(
            AccountProfile.root_profile_photo_folder_key)
        cover_full_folder = model.full_folder_path(
            AccountProfile.root_cover_photo_folder_key)

        if 'profile_photo' in request.files:
            profile_path, profile_name, ferrors = store_file(
                acctprofilephoto, request.files['profile_photo'],
                sub_folder=sub_folder, full_folder=profile_full_folder,
                not_local=True)
            if ferrors:
                return ferrors['message'], ferrors['code']
            profile_data['files'][profile_name] = profile_path
        if 'cover_photo' in request.files:
            cover_path, cover_name, ferrors = store_file(
                acctcoverphoto, request.files['cover_photo'],
                sub_folder=sub_folder, full_folder=cover_full_folder,
                not_local=True)
            if ferrors:
                return ferrors['message'], ferrors['code']
            cover_data['files'][cover_name] = cover_path

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
                            [model.profile_thumbnail], sub_folder=sub_folder,
                            full_folder=profile_full_folder,
                            is_thumbnail=True)
                        if th_errors:
                            return th_errors['message'], th_errors['code']

        if 'cover_photo' in request.form:
            cover_data['delete'] = []
            if request.form['cover_photo'] == model.cover_photo:
                cover_data['delete'].append(request.form['cover_photo'])
                if cover_data['delete']:
                    # delete all mentioned files
                    ferrors = delete_files(
                        cover_data['delete'], sub_folder=sub_folder,
                        full_folder=cover_full_folder)
                    if ferrors:
                        return ferrors['message'], ferrors['code']
                    # when cover photo delete cover thumbnail also delete
                    if model.cover_thumbnail:
                        th_errors = delete_files(
                            [model.cover_thumbnail], sub_folder=sub_folder,
                            full_folder=profile_full_folder,
                            is_thumbnail=True)
                        if th_errors:
                            return th_errors['message'], th_errors['code']

        # get the json data from the request
        try:
            json_data = request.form.to_dict()
            if 'management_profiles' in json_data:
                json_data.pop('management_profiles')

            if (not json_data and  # <- no text data
                    not profile_data['files'] and  # <- no profile photo upload
                    not cover_data['files'] and (  # <- no cover photo upload
                    'delete' not in profile_data or  # no profile photo delete
                    not profile_data['delete']) and (
                    'delete' not in cover_data or  # <- no cover photo delete
                    not cover_data['delete'])):
                # no data of any sort
                c_abort(400)
            # validate and deserialize input
            data = None
            if json_data:
                data, errors = account_profile_schema.load(
                    json_data, instance=model, partial=True)
                if errors:
                    c_abort(422, errors=errors)
            if not data:
                data = model
            # photo upload
            if profile_data and (profile_data['files'] or
                                 'delete' in profile_data):
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
            if cover_data and (cover_data['files'] or 'delete' in cover_data):
                # parse new files
                if cover_data['files']:
                    data.cover_photo = [
                        cover_name for cover_name
                        in cover_data['files']][0]
                # any old files to delete
                if 'delete' in cover_data:
                    for cover_name in cover_data['delete']:
                        if cover_name == data.cover_photo:
                            data.cover_photo = None
                            data.cover_thumbnail = None

            db.session.add(data)
            db.session.commit()
            if profile_path:
                convert_file_into_thumbnail.s(
                    True, data.row_id, APP.MOD_ACCOUNT_PROFILE,
                    profile_path, 'profile').delay()
            if cover_path:
                convert_file_into_thumbnail.s(
                    True, data.row_id, APP.MOD_ACCOUNT_PROFILE,
                    cover_path, 'cover').delay()
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

        return {'message': 'Updated Account Profile id: %s' %
                           str(model.account_id)}, 200

    @swag_from('swagger_docs/account_profile_get.yml')
    def get(self, account_id):
        """
        Get an account by id
        """
        account_profile_schema = AccountProfileSchema()
        model = None
        try:
            # first find model
            model = AccountProfile.query.filter_by(
                account_id=account_id).join(
                CFollow, and_(
                    CFollow.company_id == AccountProfile.account_id,
                    CFollow.sent_by == g.current_user['row_id']),
                isouter=True).join(
                Account, and_(
                    AccountProfile.account_id == Account.parent_account_id,
                    Account.parent_account_id == account_id),
                isouter=True).options(
                    # let it know that this is already loaded
                    contains_eager(AccountProfile.followed),
                    joinedload(AccountProfile.child_accounts),
                    # load only certain columns from joined table
                    # #TODO: make this work later
                    Load(CFollow).load_only('row_id', 'company_id', 'sent_by'),
                    # load the account name
                    joinedload(AccountProfile.account).load_only(
                        'account_name')).first()

            if model is None or model.deleted:
                c_abort(404, message='Account Profile id: %s does not exist' %
                                     str(account_id))

            result = account_profile_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class AccountProfileNoAuthAPI(BaseResource):

    @swag_from('swagger_docs/account_profile_get.yml')
    def get(self, account_id):
        """
        Get an account by id
        """
        account_profile_schema = AccountProfileSchema()
        try:
            # first find model
            model = AccountProfile.query.filter_by(
                account_id=account_id).join(
                Account, and_(
                    AccountProfile.account_id == Account.parent_account_id,
                    Account.parent_account_id == account_id),
                isouter=True).options(
                    # let it know that this is already loaded
                    joinedload(AccountProfile.child_accounts),
                    joinedload(AccountProfile.account).load_only(
                        'account_name')).first()

            if model is None or model.deleted:
                c_abort(404, message='Account Profile id: %s does not exist' %
                                     str(account_id))
            if model.account_type != ACCOUNT.ACCT_CORPORATE:
                c_abort(403)

            result = account_profile_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class AccountProfileListAPI(AuthResource):
    """
    Read API for account profile lists, i.e, more than 1 account profile
    """
    model_class = AccountProfile

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = [
            'account', 'followed', 'management_profiles', 'sector', 'industry',
            'profile_thumbnail_url', 'cover_photo_url', 'cover_thumbnail_url',
            'profile_photo_url', 'child_accounts']
        super(AccountProfileListAPI, self).__init__(*args, **kwargs)

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
        account_name = ""
        not_of_account_type = None
        if extra_query:
            if "account_name" in extra_query and extra_query[
                    'account_name']:
                account_name = '%' + (
                    extra_query["account_name"]).lower() + '%'
            if 'not_of_account_type' in extra_query and extra_query[
                    'not_of_account_type']:
                not_of_account_type = extra_query['not_of_account_type']
            if ('is_account_active' in extra_query and
                    (extra_query['is_account_active'] or
                     not extra_query['is_account_active'])):
                if not extra_query['is_account_active']:
                    query_filters['base'].append(
                        Account.activation_date.is_(None))
                else:
                    query_filters['base'].append(
                        Account.activation_date.isnot(None))
            if ('parent_account_id' in extra_query and
                    extra_query['parent_account_id']):
                query_filters['base'].append(
                    Account.parent_account_id == extra_query[
                        'parent_account_id'])
        if account_name == "":
            account_name = '%%'

        if sort:
            mapper = inspect(Account)
            sort_fxn = 'asc'
            if sort['sort'] == 'dsc':
                sort_fxn = 'desc'
            for sby in sort['sort_by']:
                if sby in mapper.columns:
                    order.append(getattr(mapper.columns[sby], sort_fxn)())

        query_filters['base'].append(and_(
            AccountProfile.account_type != ACCOUNT.ACCT_GUEST,
            AccountProfile.account_type != ACCOUNT.ACCT_ADMIN))
        if not_of_account_type:
            query_filters['base'].append(
                AccountProfile.account_type != not_of_account_type)

        query = self._build_final_query(query_filters, query_session, operator)
        # eager load 'account_name', followed status
        query = query.join(
            CFollow, and_(
                CFollow.company_id == AccountProfile.account_id,
                CFollow.sent_by == g.current_user['row_id']),
            isouter=True).join(
            Account, AccountProfile.account_id == Account.row_id).options(
                # let it know that this is already loaded
                contains_eager(AccountProfile.followed),
                # load only certain columns from joined table
                # #TODO: make this work later
                Load(CFollow).load_only('row_id', 'company_id', 'sent_by'),
                joinedload(AccountProfile.management_profiles)).filter(
                func.lower(Account.account_name).like(account_name))

        # is_account_active filter not there so all active accounts will be
        # come first then inactive account will come
        if 'is_account_active' not in extra_query:
            # for inactive account
            inactive_query = query.filter(
                Account.activation_date.is_(None)).order_by(*order)
            # for active account
            query = query.filter(
                Account.activation_date.isnot(None)).order_by(*order)

            final_query = query.union_all(inactive_query)

            final_query = final_query.join(
                CFollow, and_(
                    CFollow.company_id == AccountProfile.account_id,
                    CFollow.sent_by == g.current_user['row_id']),
                isouter=True).join(
                Account, AccountProfile.account_id == Account.row_id).options(
                # let it know that this is already loaded
                contains_eager(AccountProfile.followed),
                # load only certain columns from joined table
                # #TODO: make this work later
                Load(CFollow).load_only('row_id', 'company_id', 'sent_by'),
                joinedload(AccountProfile.management_profiles)).filter(
                func.lower(Account.account_name).like(account_name))
            # order by already used so order will be empty
            order = []
        else:
            final_query = query

        return final_query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/account_profile_get_list.yml')
    def get(self):
        """
        Get the list
        """
        account_profile_read_schema = AccountProfileReadArgsSchema(strict=True)
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            account_profile_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(AccountProfile), operator)
            # making a copy of the main output schema
            account_profile_schema = AccountProfileListSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                account_profile_schema = AccountProfileListSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching accounts found')
            result = account_profile_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class AccountProfileNoAuthListAPI(BaseResource):
    """
    Read API for account profile lists, i.e, more than 1 account profile
    """
    model_class = AccountProfile

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = [
            'account', 'followed', 'management_profiles', 'sector', 'industry',
            'profile_thumbnail_url', 'cover_photo_url', 'cover_thumbnail_url',
            'profile_photo_url', 'child_accounts']
        super(AccountProfileNoAuthListAPI, self).__init__(*args, **kwargs)

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
        account_name = '%%'
        if extra_query:
            if "account_name" in extra_query and extra_query[
                    'account_name']:
                account_name = '%' + (
                    extra_query["account_name"]).lower() + '%'
            if ('parent_account_id' in extra_query and
                    extra_query['parent_account_id']):
                query_filters['base'].append(
                    Account.parent_account_id == extra_query[
                        'parent_account_id'])

        if sort:
            mapper = inspect(Account)
            sort_fxn = 'asc'
            if sort['sort'] == 'dsc':
                sort_fxn = 'desc'
            for sby in sort['sort_by']:
                if sby in mapper.columns:
                    order.append(getattr(mapper.columns[sby], sort_fxn)())

        query_filters['base'].append(
            AccountProfile.account_type == ACCOUNT.ACCT_CORPORATE
        )

        query = self._build_final_query(query_filters, query_session, operator)
        query = query.join(
                Account, AccountProfile.account_id == Account.row_id).options(
                joinedload(AccountProfile.management_profiles)).filter(
                func.lower(Account.account_name).like(account_name))

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/account_profile_get_list.yml')
    def get(self):
        """
        Get the list
        """
        account_profile_read_schema = AccountProfileReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            account_profile_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(AccountProfile), operator)
            # making a copy of the main output schema
            account_profile_schema = AccountProfileListSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                account_profile_schema = AccountProfileListSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching accounts found')
            result = account_profile_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class AccountProfileTeamListAPI(AuthResource):
    """
    Get a team members(user profiles) by account id
    """

    model_class = UserProfile

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['cover_photo_url', 'profile_photo_url',
                                    'connected', 'contact_requested',
                                    'designation_link']
        super(AccountProfileTeamListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        designation_sort = False
        if 'designation' in sort['sort_by']:
            sort['sort_by'].remove('designation')
            designation_sort = True
        query_filters, extra_query, db_projection, s_projection, order, \
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)
        # build specific extra queries filters
        if extra_query:
            if 'full_name' in extra_query and extra_query['full_name']:
                full_name = '%' + (extra_query['full_name']).lower() + '%'
                query_filters['filters'].append(func.concat(
                    func.lower(UserProfile.first_name),
                    ' ',
                    func.lower(UserProfile.last_name)).like(full_name))

        query_filters['base'].append(User.deactivated.is_(False))

        query = self._build_final_query(query_filters, query_session, operator)
        # eager load contact and contact request table for connected status
        query = query.join(
            Contact, or_(and_(
                Contact.sent_to == g.current_user['row_id'],
                Contact.sent_by == UserProfile.user_id), and_(
                Contact.sent_to == UserProfile.user_id,
                Contact.sent_by == g.current_user['row_id'])),
            isouter=True).join(
            ContactRequest, or_(and_(
                ContactRequest.sent_to == g.current_user['row_id'],
                ContactRequest.sent_by == UserProfile.user_id,
                ContactRequest.status == CONREQUEST.CRT_SENT), and_(
                ContactRequest.sent_to == UserProfile.user_id,
                ContactRequest.sent_by == g.current_user['row_id'],
                ContactRequest.status == CONREQUEST.CRT_SENT)),
            isouter=True).join(
            User, UserProfile.user_id == User.row_id).options(
            # let it know that this is already loaded
            contains_eager(UserProfile.connected),
            contains_eager(UserProfile.contact_requested),
            # load only certain columns from joined tables
            # #TODO: make this work later
            Load(Contact).load_only('row_id', 'sent_by', 'sent_to'),
            Load(ContactRequest).load_only(
                'row_id', 'sent_by', 'sent_to', 'status',
                'accepted_rejected_on'),
            # load the account name
            joinedload(UserProfile.user).load_only('account_id'))
        query = query.join(
            AccountProfile,
            UserProfile.account_id == AccountProfile.account_id).filter(
            User.unverified.is_(False))
        if designation_sort:
            query = query.join(
                Designation, Designation.name == UserProfile.designation,
                isouter=True)
            sort_fxn = 'asc'
            if sort['sort'] == 'dsc':
                sort_fxn = 'desc'
            order.insert(0, getattr(Designation.sequence, sort_fxn)())

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/account_profile_team_get_list.yml')
    def get(self):
        """
        Get the list
        """

        account_profile_team_read_schema = AccountProfileTeamReadArgsSchema(
            strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            account_profile_team_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(UserProfile), operator)
            # making a copy of the main output schema
            user_profile_schema = UserProfileSchema(exclude=['user'])
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                user_profile_schema = UserProfileSchema(
                    only=s_projection, exclude=['user'])
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching users found')
            result = user_profile_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data, 'total': total}, 200


class AccountProfileTeamNoAuthListAPI(BaseResource):
    """
    Get a team members(user profiles) by account id
    """

    model_class = UserProfile

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['cover_photo_url', 'profile_photo_url',
                                    'connected', 'contact_requested']
        super(AccountProfileTeamNoAuthListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        designation_sort = False
        if 'designation' in sort['sort_by']:
            sort['sort_by'].remove('designation')
            designation_sort = True
        query_filters, extra_query, db_projection, s_projection, order, \
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)
        # build specific extra queries filters
        if extra_query:
            if 'full_name' in extra_query and extra_query['full_name']:
                full_name = '%' + (extra_query['full_name']).lower() + '%'
                query_filters['filters'].append(func.concat(
                    func.lower(UserProfile.first_name),
                    ' ',
                    func.lower(UserProfile.last_name)).like(full_name))

        query_filters['base'].append(User.deactivated.is_(False))

        query = self._build_final_query(query_filters, query_session, operator)
        query = query.join(
            User, UserProfile.user_id == User.row_id).join(
            AccountProfile,
            UserProfile.account_id == AccountProfile.account_id).filter(
            User.unverified.is_(False))
        if designation_sort:
            query = query.join(
                Designation, Designation.name == UserProfile.designation,
                isouter=True)
            sort_fxn = 'asc'
            if sort['sort'] == 'dsc':
                sort_fxn = 'desc'
            order.insert(0, getattr(Designation.sequence, sort_fxn)())

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/account_profile_team_get_list.yml')
    def get(self):
        """
        Get the list
        """

        account_profile_team_read_schema = AccountProfileTeamReadArgsSchema(
            strict=True)
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            account_profile_team_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(UserProfile), operator)
            db_projection = ['user_id', 'first_name', 'last_name',
                             'designation']
            # making a copy of the main output schema
            user_profile_schema = UserProfileSchema(
                only=db_projection+['account.account_name',
                                    'profile_photo_url'])
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                user_profile_schema = UserProfileSchema(
                    only=s_projection, exclude=['user'])
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching users found')
            result = user_profile_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data, 'total': total}, 200