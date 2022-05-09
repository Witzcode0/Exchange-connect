"""
Schemas for "user" related models
"""

import base64

from flask import g
from marshmallow import (
    fields, validate, pre_dump, ValidationError, validates_schema, pre_load)
from marshmallow_sqlalchemy import field_for

from app import ma, jwt, db
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.users.models import User
from app.resources.users import constants as USER
from app.resources.accounts.models import Account
from app.resources.accounts import constants as ACCOUNT
from app.base import constants as APP


@jwt.user_claims_loader
def add_claims_to_access_token(identity):
    return {
        'hello': identity,
        'foo': ['bar', 'baz']
    }


# account details that will be passed while populating account relation
account_fields = ['row_id', 'links', 'account_name', 'account_type', 'domain']
# role details that will be passed while populating role relation
role_fields = ['row_id', 'links', 'name']


class UserSchema(ma.ModelSchema):
    """
    Schema for loading "user" from request, and also formatting output
    """

    # default fields to exclude from the schema for speed up
    _default_exclude_fields = [
        'cities', 'companies', 'company_pages', 'contact_requests_sent',
        'contact_requests_received', 'contact_sent', 'contact_received',
        'countries', 'designations', 'event_bookmarks', 'eventfiles',
        'event_invites', 'events', 'updated_events', 'feeds', 'files',
        'following', 'industries', 'news_archive', 'notifications',
        'post_comments', 'postfiles', 'post_stars', 'posts', 'updated_posts',
        'sectors', 'states', 'survey', 'survey_responses', 'newswire_posts',
        'updated_newswire_posts', 'newswire_postfiles', 'created_tickets',
        'created_comments', 'assigned_tickets', 'de_peer_group',
        'webinar_answers', 'webinars_attended', 'webinar_chats',
        'webinar_hosts_created', 'webinars_hosted', 'webinars_invited',
        'webinars_created', 'webinars_participated', 'webinar_questions',
        'webinar_rsvps_created', 'webinars', 'webcast_answers', 'webcasts_hosted',
        'corporate_access_events_attended', 'webcasts_participated',
        'corporate_access_event_colls_created', 'webcasts_created',
        'corporate_access_events_collaboratored', 'webcast_hosts_created',
        'corporate_access_event_hosts_created', 'webcast_settings',
        'corporate_access_events_hosted', 'corporate_access_event_inquiries',
        'corporate_access_events_invited', 'webcast_rsvps_created',
        'corporate_access_event_participants_created', 'webcasts_attended',
        'corporate_access_events_participated', 'webcasts_invited',
        'corporate_access_event_rsvps_created', 'disallowed_slots',
        'corporate_access_event_slots_created', 'corporate_access_events',
        'corporate_access_ref_event_sub_types_created', 'webcast_questions',
        'corporate_access_ref_event_types_created', 'assigned_projects',
        'webcasts',  'project_analysts', 'project_chats', 'projects',
        'project_files', 'project_parameters', 'project_screen_sharing',
        'inquiry_edited', 'inquiry_created', 'ca_open_meetings',
        'account_user_member_creator', 'ca_open_meeting_inquiries',
        'account_user_member', 'ca_open_meeting_inquiry_history',
        'ca_open_meeting_invited', 'ca_open_meeting_participants_created',
        'ca_open_meeting_participated', 'ca_open_meeting_participated_j',
        'ca_open_meeting_slots_created', 'corporate_access_event_hosted',
        'corporate_access_event_inquiry_history', 'webinar_hosted',
        'corporate_access_event_invited', 'corporate_access_event_participated',
        'webcast_invited', 'webcast_participated', 'webinar_invited',
        'webinar_participated', 'open_meeting_invited', 'crm_contact_grouped',
        'events_joined_invitees', 'webcast_hosted', 'meeting_disallowed_slots']

    email = field_for(User, 'email', field_class=fields.Email)
    password = field_for(User, 'password', validate=validate.Regexp(
        APP.STRONG_PASSWORD))
    role_id = field_for(User, 'role_id', allow_none=True)
    profile = ma.Nested(
        'app.resources.user_profiles.schemas.UserProfileSchema',
        exclude=['user_id', 'user'], required=True)
    settings = ma.Nested(
        'app.resources.user_settings.schemas.UserSettingsSchema',
        exclude=['user_id', 'user'])
    unsubscriptions = ma.Nested(
        'app.resources.unsubscriptions.schemas.UnsubscriptionSchema',
        exclude=['email', 'created_date', 'modified_date','users'], dump_only=True)

    class Meta:
        model = User
        include_fk = True
        load_only = (
            'deleted', 'updated_by', 'created_by', 'password', 'token_key')
        dump_only = default_exclude + (
            'updated_by', 'created_by', 'deleted', 'unverified', 'settings',
            'current_notification_count', 'last_login', 'last_logout',
            'sequence_id', 'token_key', 'verify_mail_sent')
        exclude = ('account_type', 'unsuccessful_login_count')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.userapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.userlistapi')
    }, dump_only=True)

    login_locked = fields.Boolean(dump_only=True)

    @pre_dump(pass_many=True)
    def load_login_locked(self, objs, many):
        """
        Loads the login locked status of user
        """
        if many:
            for obj in objs:
                obj.load_login_locked()
        else:
            objs.load_login_locked()

    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True)
    role = ma.Nested(
        'app.resources.roles.schemas.RoleSchema', only=role_fields,
        dump_only=True)
    crm_contact_grouped = ma.List(ma.Nested(
        'app.crm_resources.crm_groups.schemas.CRMGroupSchema', only=[
            'row_id', 'group_name']), dump_only=True)

    @pre_load(pass_many=True)
    def convert_email_and_password(self, objs, many):
        """
        Covert email and password from base64 to string
        :return:
        """
        if 'password' in objs and objs['password']:
            objs['password'] = base64.b64decode(
                objs['password']).decode('utf-8')


class UserEditSchema(UserSchema):
    """
    Schema to make account_id as read only, by adding it in dump-only.
    """

    class Meta:
        dump_only = default_exclude + (
            'updated_by', 'created_by', 'deleted', 'unverified', 'settings',
            'current_notification_count', 'account_id', 'last_login',
            'last_logout', 'sequence_id', 'token_key')


class UserListSchema(UserSchema):
    """
    Schema for formatting user list output, making a separate one to load only
    certain attributes of a user profile
    """
    profile = ma.Nested(
        'app.resources.user_profiles.schemas.UserProfileSchema',
        only=['first_name', 'last_name', 'company', 'designation',
              'phone_number', 'fax', 'sector_ids', 'industry_ids',
              'profile_thumbnail_url'])


class UserReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "user" filters from request args
    """
    # standard db fields
    email = fields.String(load_only=True)
    account_id = fields.Integer(load_only=True)
    full_name = fields.String(load_only=True)
    account_type = fields.String(load_only=True, validate=validate.OneOf(
        ACCOUNT.ACCT_TYPES))
    designation = fields.String(load_only=True)
    account_name = fields.String(load_only=True)
    sector_id = fields.Integer(load_only=True)
    industry_id = fields.Integer(load_only=True)
    is_registration_request = fields.Boolean(load_only=True)
    role_id = fields.Integer(load_only=True)
    role_name = fields.String(load_only=True)
    sort_by = fields.List(fields.String(), load_only=True, missing=[
        'sequence_id'])
    deactivated = fields.Boolean(load_only=True)
    need_admins = fields.Boolean(load_only=True)
    role_names = fields.List(fields.String())


class FirstTimeChangePasswordSchema(ma.Schema):
    """
    Schema for first time change password
    """
    new_password = fields.String(
        required=True, validate=validate.Regexp(APP.STRONG_PASSWORD))

    @pre_load(pass_many=True)
    def convert_email_and_password(self, objs, many):
        """
        Covert email and password from base64 to string
        :return:
        """
        if 'new_password' in objs and objs['new_password']:
            objs['new_password'] = base64.b64decode(
                objs['new_password']).decode('utf-8')

        if 'old_password' in objs and objs['old_password']:
            objs['old_password'] = base64.b64decode(
                objs['old_password']).decode('utf-8')


class ChangePasswordSchema(FirstTimeChangePasswordSchema):
    """
    Schema for change password by user
    """
    old_password = fields.String(required=True)


class UserOrderSchema(ma.Schema):
    """
    schema for loading "users" from request
    """

    user_ids = fields.List(fields.Integer(), required=True)
    account_id = None

    def load_account_id(self, data):
        """
        validate and fetch account_id for users validation
        """
        ref_acc_id = g.current_user['account']['row_id']
        account = Account.query.filter_by(
            row_id=ref_acc_id).first()
        if account:
            self.account_id = ref_acc_id
        else:
            raise ValidationError(
                'Account id: %s does not exist'
                % str(ref_acc_id),
                'account_id')

        return self.account_id

    @validates_schema(pass_original=True)
    def validate_users(self, data, original_data):
        """
        validate users
        """
        error = False  # error flag
        ref_acc_id = self.load_account_id(data)
        fetched_ids = []
        missing = []  # row_ids for which users doesn't exists

        # fetch the users for the given row_ids and account_id
        if ('user_ids' in original_data and
                original_data['user_ids']):
            row_ids = original_data['user_ids']
            users = User.query.filter(User.account_id == ref_acc_id,
                                      User.row_id.in_(row_ids)).all()

            # check if user for all given row_ids exists or not
            if users:
                for user in users:
                    fetched_ids.append(user.row_id)
            missing = set(row_ids) - set(fetched_ids)

        if missing:
            error = True

        if error:
            raise ValidationError(
                'Either users: %s do not exist or does not '
                'have same account_id' % missing,
                'users')


class AdminUserOrderSchema(UserOrderSchema):
    """
    Schema for loading user from admin PUT API
    """

    account_id = fields.Integer(required=True)

    def load_account_id(self, data):
        """
        validate account_id for users validation
        """
        # check account_id exist or not
        if 'account_id' in data:
            ref_account = Account.query.filter_by(
                row_id=data['account_id']).first()
            if ref_account:
                self.account_id = ref_account.row_id
            else:
                raise ValidationError(
                    'Account id: %s does not exist'
                    % str(data['account_id']),
                    'account_id')

        return self.account_id
