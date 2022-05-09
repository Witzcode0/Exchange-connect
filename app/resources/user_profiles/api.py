"""
API endpoints for "user profile" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g, json
from flask_restful import abort
from sqlalchemy.inspection import inspect
from sqlalchemy import cast, and_, or_, func, any_
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only, joinedload, contains_eager, Load
from flasgger.utils import swag_from

from app import db, c_abort, usrprofilephoto, usrcoverphoto
from app.base.api import AuthResource
from app.common.helpers import store_file, delete_files
from app.resources.users.models import User
from app.resources.user_profiles.models import UserProfile
from app.resources.user_profiles.schemas import (
    UserProfileSchema, UserProfileReadArgsSchema, UserProfileSingleGetSchema)
from app.resources.users.schemas import UserSchema
from app.resources.contact_requests import constants as CONREQUEST
from app.resources.contact_requests.models import ContactRequest
from app.resources.contacts.models import Contact
from app.resources.accounts import constants as ACCOUNT
from app.base import constants as APP
from app.resources.account_profiles.models import AccountProfile
from app.resources.user_settings.models import UserSettings
from app.resources.user_settings.schemas import UserSettingsSchema
from app.resources.accounts.models import Account
from app.resources.roles.schemas import RoleSchema
from app.resources.roles.models import Role
from app.resources.menu.models import Menu
from app.resources.menu.schemas import MenuSchema
from app.resources.roles.helpers import add_permissions_to_menus
from app.resources.menu.helpers import keep_only_active_menus
from app.resources.accounts.models import Account

from queueapp.thumbnail_tasks import convert_file_into_thumbnail


class UserProfileAPI(AuthResource):
    """
    CRUD API for user profile
    """

    @swag_from('swagger_docs/user_profile_put.yml')
    def put(self):
        """
        Update a user profile, either pass file data as multipart-form,
        or json data
        """

        user_profile_schema = UserProfileSchema()
        user_schema = UserSchema()
        user_setting_schema = UserSettingsSchema()
        # first find model
        model = None
        try:
            model = UserProfile.query.options(joinedload(
                UserProfile.user)).filter_by(
                user_id=g.current_user['row_id']).first()
            if model is None or model.deleted:
                c_abort(404, message='User Profile id: %s does not exist' %
                                     str(g.current_user['row_id']))
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
            UserProfile.root_profile_photo_folder_key)
        cover_full_folder = model.full_folder_path(
            UserProfile.root_cover_photo_folder_key)

        # save files
        if 'profile_photo' in request.files:
            profile_path, profile_name, ferrors = store_file(
                usrprofilephoto, request.files['profile_photo'],
                sub_folder=sub_folder, full_folder=profile_full_folder,
                not_local=True)
            if ferrors:
                return ferrors['message'], ferrors['code']
            profile_data['files'][profile_name] = profile_path
        if 'cover_photo' in request.files:
            cover_path, cover_name, ferrors = store_file(
                usrcoverphoto, request.files['cover_photo'],
                sub_folder=sub_folder, full_folder=cover_full_folder,
                not_local=True)
            if ferrors:
                return ferrors['message'], ferrors['code']
            cover_data['files'][cover_name] = cover_path

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

        try:
            # get the json data from the request
            json_data = request.form.to_dict()
            if 'experiences' in json_data:
                del json_data['experiences']
                json_data['experience'] = json.loads(
                    request.form['experiences'])
            if 'educations' in json_data:
                del json_data['educations']
                json_data['education'] = json.loads(
                    request.form['educations'])
            if 'skills[]' in json_data:
                json_data['skills'] = request.form.getlist('skills[]')
            if 'interests[]' in json_data:
                json_data['interests'] = request.form.getlist('interests[]')
            if 'sector_ids' in json_data:
                json_data['sector_ids'] = request.form.getlist('sector_ids')
            if 'industry_ids' in json_data:
                json_data['industry_ids'] = request.form.getlist(
                    'industry_ids')

            if (not json_data and  # <- no text data
                    not profile_data['files'] and  # <- no profile photo upload
                    not cover_data['files'] and (  # <- no cover photo upload
                    'delete' not in profile_data or  # no profile photo delete
                    not profile_data['delete']) and (
                    'delete' not in cover_data or  # <- no cover photo delete
                    not cover_data['delete'])):
                # no data of any sort
                c_abort(400)

            user_data = None
            if 'search_privacy[]' in json_data:
                json_user = {}
                json_user['search_privacy'] = request.form.getlist(
                    'search_privacy[]')
                user_data, errors = user_setting_schema.load(
                    json_user, instance=model.user.settings, partial=True)
                if errors:
                    c_abort(422, errors=errors)
                db.session.add(user_data)
                db.session.commit()

            # validate and deserialize input
            data = None
            if json_data:
                data, errors = user_profile_schema.load(
                    json_data, instance=model, partial=True)
                if errors:
                    c_abort(422, errors=errors)
            if not data:
                data = model

            # profile photo upload
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
            # cover photo upload
            if cover_data and (cover_data['files'] or
                               'delete' in cover_data):
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

            if not model.user.f_profile_updated:
                model.user.f_profile_updated = True
                db.session.add(model.user)
            db.session.add(data)
            db.session.commit()
            if profile_path:
                convert_file_into_thumbnail.s(
                    True, data.row_id, APP.MOD_USER_PROFILE,
                    profile_path, 'profile').delay()
            if cover_path:
                convert_file_into_thumbnail.s(
                    True, data.row_id, APP.MOD_USER_PROFILE,
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
        return {'message': 'Updated User Profile id: %s' %
                           str(model.user_id)}, 200

    @swag_from('swagger_docs/user_profile_get.yml')
    def get(self, user_id):
        """
        Get a user by id
        """

        model = None
        try:
            # first find model
            model = UserProfile.query.filter_by(
                user_id=user_id).join(
                Contact, or_(and_(Contact.sent_to == UserProfile.user_id,
                                  Contact.sent_by == g.current_user['row_id']),
                             and_(Contact.sent_to == g.current_user['row_id'],
                                  Contact.sent_by == UserProfile.user_id)),
                isouter=True).join(ContactRequest, or_(and_(
                    ContactRequest.sent_to == UserProfile.user_id,
                    ContactRequest.sent_by == g.current_user['row_id'],
                    ContactRequest.status == CONREQUEST.CRT_SENT),
                    and_(ContactRequest.sent_to == g.current_user['row_id'],
                         ContactRequest.sent_by == UserProfile.user_id,
                         ContactRequest.status == CONREQUEST.CRT_SENT)),
                isouter=True).options(
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
                joinedload(UserProfile.user).load_only('account_id')).first()

            if model is None or model.deleted:
                c_abort(404, message='User Profile id: %s does not exist' %
                                     str(user_id))

            result = UserProfileSingleGetSchema().dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class DesignLabUserProfileAPI(AuthResource):
    """
    CRUD API for user profile
    """

    @swag_from('swagger_docs/user_profile_put.yml')
    def put(self):
        """
        Update a user profile, either pass file data as multipart-form,
        or json data
        """

        user_profile_schema = UserProfileSchema()
        user_schema = UserSchema()
        user_setting_schema = UserSettingsSchema()
        # first find model
        model = None
        try:
            model = UserProfile.query.options(joinedload(
                UserProfile.user)).filter_by(
                user_id=g.current_user['row_id']).first()
            if model is None or model.deleted:
                c_abort(404, message='User Profile id: %s does not exist' %
                                     str(g.current_user['row_id']))
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
            UserProfile.root_profile_photo_folder_key)
        cover_full_folder = model.full_folder_path(
            UserProfile.root_cover_photo_folder_key)

        # save files
        if 'profile_photo' in request.files:
            profile_path, profile_name, ferrors = store_file(
                usrprofilephoto, request.files['profile_photo'],
                sub_folder=sub_folder, full_folder=profile_full_folder,
                not_local=True)
            if ferrors:
                return ferrors['message'], ferrors['code']
            profile_data['files'][profile_name] = profile_path
        if 'cover_photo' in request.files:
            cover_path, cover_name, ferrors = store_file(
                usrcoverphoto, request.files['cover_photo'],
                sub_folder=sub_folder, full_folder=cover_full_folder,
                not_local=True)
            if ferrors:
                return ferrors['message'], ferrors['code']
            cover_data['files'][cover_name] = cover_path

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

        try:
            # get the json data from the request
            json_data = request.form.to_dict()
            if 'experiences' in json_data:
                del json_data['experiences']
                json_data['experience'] = json.loads(
                    request.form['experiences'])
            if 'educations' in json_data:
                del json_data['educations']
                json_data['education'] = json.loads(
                    request.form['educations'])
            if 'skills[]' in json_data:
                json_data['skills'] = request.form.getlist('skills[]')
            if 'interests[]' in json_data:
                json_data['interests'] = request.form.getlist('interests[]')
            if 'sector_ids' in json_data:
                json_data['sector_ids'] = request.form.getlist('sector_ids')
            if 'industry_ids' in json_data:
                json_data['industry_ids'] = request.form.getlist(
                    'industry_ids')

            if (not json_data and  # <- no text data
                    not profile_data['files'] and  # <- no profile photo upload
                    not cover_data['files'] and (  # <- no cover photo upload
                    'delete' not in profile_data or  # no profile photo delete
                    not profile_data['delete']) and (
                    'delete' not in cover_data or  # <- no cover photo delete
                    not cover_data['delete'])):
                # no data of any sort
                c_abort(400)

            user_data = None
            if 'search_privacy[]' in json_data:
                json_user = {}
                json_user['search_privacy'] = request.form.getlist(
                    'search_privacy[]')
                user_data, errors = user_setting_schema.load(
                    json_user, instance=model.user.settings, partial=True)
                if errors:
                    c_abort(422, errors=errors)
                db.session.add(user_data)
                db.session.commit()

            # validate and deserialize input
            data = None
            if json_data:
                data, errors = user_profile_schema.load(
                    json_data, instance=model, partial=True)
                if errors:
                    c_abort(422, errors=errors)
            if not data:
                data = model

            # profile photo upload
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
            # cover photo upload
            if cover_data and (cover_data['files'] or
                               'delete' in cover_data):
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

            if not model.user.f_profile_updated:
                model.user.f_profile_updated = True
                db.session.add(model.user)
            db.session.add(data)
            db.session.commit()
            if profile_path:
                convert_file_into_thumbnail.s(
                    True, data.row_id, APP.MOD_USER_PROFILE,
                    profile_path, 'profile').delay()
            if cover_path:
                convert_file_into_thumbnail.s(
                    True, data.row_id, APP.MOD_USER_PROFILE,
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
        return {'message': 'Updated User Profile id: %s' %
                           str(model.user_id)}, 200

    @swag_from('swagger_docs/user_profile_get.yml')
    def get(self, user_id):
        """
        Get a user by id
        """

        model = None
        try:
            # first find model
            model = UserProfile.query.filter_by(
                user_id=user_id).join(
                Contact, or_(and_(Contact.sent_to == UserProfile.user_id,
                                  Contact.sent_by == g.current_user['row_id']),
                             and_(Contact.sent_to == g.current_user['row_id'],
                                  Contact.sent_by == UserProfile.user_id)),
                isouter=True).join(ContactRequest, or_(and_(
                    ContactRequest.sent_to == UserProfile.user_id,
                    ContactRequest.sent_by == g.current_user['row_id'],
                    ContactRequest.status == CONREQUEST.CRT_SENT),
                    and_(ContactRequest.sent_to == g.current_user['row_id'],
                         ContactRequest.sent_by == UserProfile.user_id,
                         ContactRequest.status == CONREQUEST.CRT_SENT)),
                isouter=True).options(
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
                joinedload(UserProfile.user).load_only('account_id')).first()

            if model is None or model.deleted:
                c_abort(404, message='User Profile id: %s does not exist' %
                                     str(user_id))

            result = UserProfileSingleGetSchema().dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class UserRoleAPI(AuthResource):
    """
    API for current_user role
    """

    # @swag_from('swagger_docs/user_profile_get.yml')
    def get(self):
        """
        Get current user's role.
        """

        result = {'results': []}
        try:
            # first find model
            role_id = g.current_user['role']['row_id']
            role = Role.query.get(role_id)
            if role:
                role_schema = RoleSchema(only=['role_menu_permissions'])
                role_schema.need_all_permissions = True

                role = role_schema.dump(role).data
                role_perms = role['role_menu_permissions']
                menu_ids = [x['menu']['row_id'] for x in role_perms]
                menus = Menu.query.filter(
                    Menu.row_id.in_(menu_ids),
                    Menu.parent_id.is_(None)).order_by('sequence').all()
                menus = MenuSchema(many=True).dump(menus).data
                add_permissions_to_menus(
                    menus, role_perms, False, include_all_perm=True)
                keep_only_active_menus(menus)
                result['results'] = menus

        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return result, 200


class UserProfileListAPI(AuthResource):
    """
    Read API for user profile lists, i.e, more than 1 user profile
    """

    model_class = UserProfile

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['cover_photo_url', 'profile_photo_url',
                                    'connected', 'contact_requested']
        super(UserProfileListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        account_type = filters.pop('account_type', None)
        account_name = filters.pop('company', None)
        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)
        sector_id = None
        industry_id = None
        not_of_account_type = None
        # build specific extra queries filters
        if extra_query:
            if 'sector_id' in extra_query and extra_query['sector_id']:
                sector_id = extra_query['sector_id']
            if 'industry_id' in extra_query and extra_query['industry_id']:
                industry_id = extra_query['industry_id']
            if 'full_name' in extra_query and extra_query['full_name']:
                full_name = '%' + (extra_query['full_name']).lower() + '%'
                query_filters['filters'].append(and_((func.concat(
                    func.lower(UserProfile.first_name),
                    ' ',
                    func.lower(UserProfile.last_name)).like(full_name)),
                    UserProfile.user_id != g.current_user['row_id']))
            if 'not_of_account_type' in extra_query and extra_query[
                    'not_of_account_type']:
                not_of_account_type = extra_query['not_of_account_type']
        if account_name:
            query_filters['filters'].append(
                func.lower(Account.account_name).like('%'+account_name+'%')
            )

        query_filters['base'].append(and_(
            UserProfile.account_type != ACCOUNT.ACCT_GUEST,
            UserProfile.account_type != ACCOUNT.ACCT_ADMIN,
            UserProfile.user_id != g.current_user['row_id'],
            User.unverified.is_(False),
            User.deactivated.is_(False)))

        # if not_of_account_type then do not display those account_type users
        if not_of_account_type:
            query_filters['base'].append(
                UserProfile.account_type != not_of_account_type)

        # search privacy filters
        sp_filters = []
        if g.current_user['account_model'].profile.sector_id:
            sp_filters.append(
                g.current_user['account_model'].profile.sector_id == any_(
                    UserSettings.search_privacy_sector))
        if g.current_user['account_model'].profile.industry_id:
            sp_filters.append(
                g.current_user['account_model'].profile.industry_id == any_(
                    UserSettings.search_privacy_industry))
        sp_filters.append(
            g.current_user['account_type'] == any_(
                UserSettings.search_privacy))
        # filter with designation wise
        if g.current_user['profile']['designation_link']:
            sp_filters.append(
                g.current_user['profile']['designation_link']
                ['designation_level'] == any_(
                    UserSettings.search_privacy_designation_level))
        if g.current_user['account_model'].profile.market_cap:
            sp_filters.append(and_(
                g.current_user['account_model'].profile.market_cap <=
                UserSettings.search_privacy_market_cap_max,
                g.current_user['account_model'].profile.market_cap >=
                UserSettings.search_privacy_market_cap_min))
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
            isouter=True).join(UserSettings, and_(
                UserProfile.user_id == UserSettings.user_id,
                *sp_filters)).join(
            User).options(
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
            UserProfile.account_id == AccountProfile.account_id)
        if account_name:
            query = query.join(
            Account,
            UserProfile.account_id == Account.row_id)
        if account_type:
            query = query.filter(UserProfile.account_type == account_type)
        if sector_id:
            query = query.filter(AccountProfile.sector_id == sector_id)
        if industry_id:
            query = query.filter(AccountProfile.industry_id == industry_id)

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/user_profile_get_list.yml')
    def get(self):
        """
        Get the list
        """

        user_profile_read_schema = UserProfileReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            user_profile_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
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
