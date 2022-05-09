"""
API endpoints for "admin accounts" package.
"""
import csv
import os
import chardet
import uuid

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy import and_, null, func, or_
from sqlalchemy.inspection import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only, joinedload
from flasgger import swag_from
from xlrd import open_workbook

from app import db, c_abort
from app.base.api import AuthResource
from app.base import constants as APP
from app.auth.decorators import role_permission_required
from app.resources.accounts.models import Account, AccountPeerGroup
from app.resources.accounts import constants as ACCOUNT
from app.resources.accounts.schemas import (
    AccountSchema, AccountReadArgsSchema, AccountPutSchema)
from app.resources.account_stats.models import AccountStats
from app.resources.account_settings.models import AccountSettings
from app.resources.roles import constants as ROLE
from app.resources.users.models import User
from app.resources.users import constants as USER
from app.resources.user_profiles.models import UserProfile
from app.resources.follows.models import CFollow, CFollowHistory
from app.resources.account_profiles.models import AccountProfile
from app.resources.account_managers.models import (
    AccountManager, AccountManagerHistory)
from app.resources.account_managers.schemas import AccountManagerSchema
from app.resources.account_user_members.helpers import (
    update_user_member_for_child_account)
from app.resources.twitter_feeds.models import TwitterFeedSource

from queueapp.twitter_feeds.fetch_tweets import fetch_tweets
from queueapp.user_stats_tasks import manage_users_stats
from queueapp.accounts.account_news import link_account_news
from queueapp.accounts.account_announcements import link_account_announcements
from queueapp.accounts.adjust_contact_count import adjust_contact_count
from app.resources.industries.models import Industry
from queueapp.accounts.account_announcements import link_account_announcements, link_account_id



class AccountAPI(AuthResource):
    """
    Create, update, delete API for accounts
    """

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[ROLE.ERT_SU])
    @swag_from('swagger_docs/account_post.yml')
    def post(self):
        """
        Create an account
        """
        account_schema = AccountSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = account_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            data.profile.account_type = data.account_type
            if data.account_manager:
                data.account_manager.created_by = data.created_by
                data.account_manager.updated_by = data.updated_by
            # create account stats
            data.stats = AccountStats()
            # add default account settings
            data.settings = AccountSettings()
            # no errors, so add data to db
            # set accepted as False, even if sent as True
            if data.account_type == ACCOUNT.ACCT_CORP_GROUP:
                data.is_parent = True
            db.session.add(data)
            db.session.commit()
            # if account type is group so child account will be update
            # with parent_account_id
            if (data.account_type == ACCOUNT.ACCT_CORP_GROUP and
                    'child_account_ids' in json_data):
                for child in account_schema._child_accounts:
                    Account.query.filter(
                        Account.row_id == child.row_id).update({
                            Account.parent_account_id: data.row_id},
                            synchronize_session=False)
                    db.session.commit()
            # for account peer groups
            if account_schema._cached_peer_ids:
                for peer_id in account_schema._cached_peer_ids:
                    if not AccountPeerGroup.query.filter(and_(
                            AccountPeerGroup.primary_account_id == data.row_id,
                            AccountPeerGroup.peer_account_id == peer_id)).first():
                        peer = AccountPeerGroup(
                            primary_account_id=data.row_id,
                            peer_account_id = peer_id,
                            created_by=data.created_by,
                            updated_by=data.updated_by)
                        db.session.add(peer)
                db.session.commit()
            if data.twitter_id:
                data.tweet_source = TwitterFeedSource(
                    screen_name=data.twitter_id)
                if not data.tweet_source.verify_user():
                    db.session.delete(data)
                    db.session.commit()
                    c_abort(422, message='Could not verify twitter account.')
                db.session.add(data.tweet_source)
                db.session.commit()
                data.tweet_source.follow_source()
                fetch_tweets.s(True, data.tweet_source.row_id).delay()
            if data.keywords:
                link_account_news.s(True, data.row_id).delay()
            if data.domain_id == 1:
                if data.identifier:
                    link_account_announcements.s(True, data.row_id).delay()
                    link_account_id.s(True, data.row_id).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (lower(account_name::text))=(abc) already exists.
                column = e.orig.diag.message_detail.split('(')[2].split(':')[0]
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

        return {'message': 'Account added: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    @swag_from('swagger_docs/account_put.yml')
    def put(self, row_id):
        """
        Update an account
        """
        account_put_schema = AccountPutSchema()
        # first find model
        model = None
        old_account_manager = None
        old_blocked = None
        old_identifier = None
        try:
            model = Account.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Account id: %s'
                        ' does not exist' % str(row_id))
            if model.account_manager:
                old_account_manager = model.account_manager
            old_blocked = model.blocked
            if model.identifier:
                old_identifier = model.identifier
            # for validate child account exists in other group account or not
            account_put_schema._check_account_type = model.account_type
            account_put_schema._check_account_id = model.row_id
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input
            account_type = model.account_type
            account_manager = None
            old_twitter_id = model.twitter_id
            old_keywords = set(model.keywords)
            if ('account_manager' in json_data and
                    json_data['account_manager']):
                account_manager = json_data.pop('account_manager')
            data, errors = account_put_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            if ('twitter_id' in json_data and
                    json_data['twitter_id'] != old_twitter_id):
                new_tweet_source = TwitterFeedSource(
                    screen_name=json_data['twitter_id'])
                if not new_tweet_source.verify_user():
                    c_abort(422, message='Could not verify twitter account.')
                if data.tweet_source:
                    data.tweet_source.unfollow_source()
                    data.tweet_source.screen_name = json_data['twitter_id']
                else:
                    data.tweet_source = new_tweet_source
                db.session.add(data.tweet_source)
                db.session.commit()
                data.tweet_source.follow_source()
                fetch_tweets.s(True, data.tweet_source.row_id).delay()

            # if account manager object there
            if (account_manager and 'row_id' not in account_manager and
                    'manager_id' in account_manager):
                account_manager['account_id'] = row_id
                manager_data, errors = AccountManagerSchema().load(
                    account_manager)
                if errors:
                    db.session.rollback()
                    c_abort(422, errors=errors)
                if old_account_manager:
                    account_manager_history = AccountManagerHistory(
                        account_id=old_account_manager.account_id,
                        manager_id=old_account_manager.manager_id,
                        created_by=old_account_manager.created_by,
                        updated_by=g.current_user['row_id'])
                    db.session.add(account_manager_history)
                    AccountManager.query.filter(
                        AccountManager.row_id == old_account_manager.row_id
                    ).delete(synchronize_session=False)
                    db.session.commit()

                manager_data.created_by = g.current_user['row_id']
                manager_data.updated_by = manager_data.created_by
                db.session.add(manager_data)

            # for account peer groups
            old_peer_ids = [c.peer_account_id for c in AccountPeerGroup.query.filter(
                AccountPeerGroup.primary_account_id == row_id).options(
                load_only('peer_account_id')).all()]
            remove_peer_ids = set(old_peer_ids) - set(account_put_schema._cached_peer_ids)
            if account_put_schema._cached_peer_ids:
                remove_peer_ids = set(old_peer_ids) - set(
                    account_put_schema._cached_peer_ids)
                for peer_id in account_put_schema._cached_peer_ids:
                    if peer_id not in old_peer_ids:
                        peer = AccountPeerGroup(
                            primary_account_id=row_id,
                            peer_account_id=peer_id,
                            created_by=data.created_by,
                            updated_by=data.updated_by)
                        db.session.add(peer)
            if remove_peer_ids:
                AccountPeerGroup.query.filter(and_(
                    AccountPeerGroup.primary_account_id == row_id,
                    AccountPeerGroup.peer_account_id.in_(list(remove_peer_ids))
                )).delete(synchronize_session=False)
                db.session.commit()
            # if new keyword is added to account scan news for linking
            if json_data.get('keywords'):
                if set(json_data.get('keywords')) - old_keywords:
                    link_account_news.s(True, data.row_id).delay()
            # if correct identifier is set to account or
            if 'identifier' in json_data and data.domain_id == 1:
                if old_identifier != json_data['identifier']:
                    link_account_announcements.s(True, data.row_id).delay()
                    link_account_id.s(True, data.row_id).delay()
            # when account is group account child parent_account_id will be
            # change
            old_child_account_ids = []
            new_child_account_ids = []
            if (data.account_type == ACCOUNT.ACCT_CORP_GROUP and
                    account_put_schema._child_accounts or (
                    'child_account_ids' in json_data and
                        not json_data['child_account_ids'])):
                # add new child account
                for child in account_put_schema._child_accounts:
                    if child not in data.child_accounts:
                        new_child_account_ids.append(child.row_id)
                        Account.query.filter(
                            Account.row_id == child.row_id
                        ).update({Account.parent_account_id: data.row_id},
                                 synchronize_session=False)
                        db.session.commit()
                # delete old child account
                for old_ch_account in data.child_accounts:
                    if (old_ch_account not in
                            account_put_schema._child_accounts or (
                            'child_account_ids' in json_data and
                                not json_data['child_account_ids'])):
                        old_child_account_ids.append(old_ch_account.row_id)
                        Account.query.filter(and_(
                            Account.parent_account_id == data.row_id,
                            Account.row_id == old_ch_account.row_id)).update(
                            {Account.parent_account_id: null()},
                            synchronize_session=False)
                        db.session.commit()
                update_user_member_for_child_account(
                    data.row_id, old_child_account_ids, new_child_account_ids)

            if account_type != data.account_type:
                data.profile.account_type = data.account_type
                # change in user data
                user_all_data = User.query.filter(
                    User.account_id == row_id,
                    User.account_type == account_type).options(load_only(
                        'row_id')).all()
                user_ids = [user.row_id for user in user_all_data]

                User.query.filter(
                    User.row_id.in_(user_ids)).update({
                        User.account_type: data.account_type},
                    synchronize_session=False)
                db.session.commit()

                # change in user_profile data
                UserProfile.query.filter(
                    UserProfile.user_id.in_(user_ids)).update({
                        UserProfile.account_type: data.account_type},
                    synchronize_session=False)
                db.session.commit()
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()
            if old_blocked != data.blocked:
                adjust_contact_count.s(True, data.row_id, data.blocked).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (lower(account_name::text))=(abc) already exists.
                column = e.orig.diag.message_detail.split('(')[2].split(':')[0]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # DETAIL: Key(manager_id) = (4) is not present in table "user".
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
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
        return {'message': 'Updated Account id: %s' %
                str(row_id)}, 200

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[ROLE.ERT_SU])
    @swag_from('swagger_docs/account_delete.yml')
    def delete(self, row_id):
        """
        Delete an account
        """
        model = None
        account_user = None
        try:
            # first find model
            model = Account.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Account id: %s'
                        ' does not exist' % str(row_id))
            # check particular account is used in user or not
            account_user = User.query.filter(
                User.account_id == row_id).first()
            if account_user:
                c_abort(
                    422, message=APP.MSG_REF_OTHER_TABLE + 'User',
                    errors={'row_id': [APP.MSG_REF_OTHER_TABLE + 'User']})
            # if model is found, and not yet deleted, delete it
            model.deleted = True
            model.profile.deleted = True
            db.session.add(model)
            db.session.commit()

            # delete follow which following particular account
            count = 0
            batch_size = 100
            cfollow_data = CFollow.query.filter(
                CFollow.company_id == row_id).options(
                load_only('sent_by', 'company_id')).all()
            CFollow.query.filter(CFollow.company_id == row_id).delete()
            db.session.commit()
            for cfollow in cfollow_data:
                count += 1
                db.session.add(CFollowHistory(
                    sent_by=cfollow.sent_by,
                    company_id=cfollow.company_id))
                if count >= batch_size:
                    db.session.commit()
                    count = 0
                # update user total_companies
                manage_users_stats.s(
                    True, cfollow.sent_by, USER.USR_COMPS,
                    increase=False).delay()
            if count:
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

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    @swag_from('swagger_docs/account_get.yml')
    def get(self, row_id):
        """
        Get an account by id
        """
        model = None
        try:
            # first find model
            model = Account.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Account id: %s'
                        ' does not exist' % str(row_id))
            result = AccountSchema(
                exclude=AccountSchema._default_exclude_fields).dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class AccountList(AuthResource):
    """
    Read API for account lists, i.e, more than 1 account
    """
    model_class = Account

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['stats', 'domain', 'profile']
        super(AccountList, self).__init__(*args, **kwargs)

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
        sector_id = None
        industry_id = None
        # build specific extra queries filters
        if extra_query:
            mapper = inspect(self.model_class)
            for f in extra_query:
                # dates
                if f in ['subscription_start_date_from',
                         'subscription_start_date_to',
                         'subscription_end_date_from',
                         'subscription_end_date_to'] and extra_query[f]:
                    # get actual field name
                    fld = f.replace('_from', '').replace('_to', '')
                    # build date query
                    if '_from' in f:
                        query_filters['filters'].append(
                            mapper.columns[fld] >= filters[f])
                        continue
                    if '_to' in f:
                        query_filters['filters'].append(
                            mapper.columns[fld] <= filters[f])
                        continue
            if 'sector_id' in extra_query and extra_query['sector_id']:
                sector_id = extra_query['sector_id']
            if 'industry_id' in extra_query and extra_query['industry_id']:
                industry_id = extra_query['industry_id']
            if ('is_account_active' in extra_query and
                    (extra_query['is_account_active'] or
                     not extra_query['is_account_active'])):
                if not extra_query['is_account_active']:
                    query_filters['base'].append(
                        Account.activation_date.is_(None))
                else:
                    query_filters['base'].append(
                        Account.activation_date.isnot(None))
        query_filters['base'].append(and_(
            Account.account_type != ACCOUNT.ACCT_GUEST,
            Account.account_name != 'Default'))
        query = self._build_final_query(
            query_filters, query_session, operator)
        query = query.join(AccountProfile)
        # if current user is manager
        if g.current_user['role']['name'] == ROLE.ERT_MNG:
            # manager can access only assigned accounts
            query = query.join(
                AccountManager, and_(
                    AccountManager.account_id == Account.row_id,
                    AccountManager.manager_id == g.current_user['row_id']))

        if sector_id:
            query = query.filter(
                AccountProfile.sector_id == sector_id)
        if industry_id:
            query = query.filter(
                AccountProfile.industry_id == industry_id)

        # is_account_active filter not there so all active accounts will be
        # come first then inactive account will come
        if 'is_account_active' not in extra_query:
            # for inactive account
            inactive_query = query.filter(
                Account.activation_date.is_(None)).order_by(*order)
            # for active account
            query = query.filter(
                Account.activation_date.isnot(None)).order_by(
                *order)

            final_query = query.union_all(inactive_query)
            # order by already used so order will be empty
            order = []
        else:
            final_query = query

        return final_query, db_projection, s_projection, order, paging

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    @swag_from('swagger_docs/account_get_list.yml')
    def get(self):
        """
        Get the list
        """
        account_read_schema = AccountReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            account_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Account), operator)
            # making a copy of the main output schema
            account_schema = AccountSchema(
                exclude=AccountSchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                account_schema = AccountSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching accounts found')
            result = account_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data, 'total': total}, 200


class UpdateSmeAccounts(AuthResource):

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    # @swag_from('swagger_docs/account_put.yml')
    def put(self):
        """
        Update sme account's stock price, currency, market cap and shares
        """
        try:
            file = request.files['filename']
            if '.csv' not in file.filename:
                c_abort(422, message='Invalid file')
            upload_path = os.path.join(
                current_app.config['BASE_UPLOADS_FOLDER'],
                'smeaccountfile')
            if not os.path.exists(upload_path):
                os.makedirs(upload_path)
            path = os.path.join(upload_path, file.filename)
            file.save(path)
            with open(path, 'rb') as f:
                result = chardet.detect(f.read())
            with open(path, 'r', newline='',
                      encoding=result['encoding']) as file:

                dialect = csv.Sniffer().sniff(file.readline())
                file.seek(0)
                reader = csv.reader(file, dialect)
                fields = next(reader)
                try:
                    id_index = fields.index('Company Id')
                    sp_index = fields.index('Stock Price')
                    share_index = fields.index('Shares O/S')
                    market_index = fields.index('Market Cap')
                    currency_index = fields.index('Currency')
                except ValueError:
                    c_abort(422, message='provide columns =  (Id, Stock Price,'
                    'Shares O/S, Market Cap, Currency) in header of csv')
                not_updated_ac_ids = []
                for row in reader:
                    account = Account.query.get(row[id_index])
                    if not account or not account.is_sme:
                        not_updated_ac_ids.append(row[id_index])
                        continue
                    market_cap = row[market_index]
                    if not market_cap:
                        market_cap = 0
                    AccountProfile.query.filter(
                        AccountProfile.account_id==row[id_index]).update(
                        {'currency': row[currency_index],
                         'market_cap': market_cap,
                         'stock_price': row[sp_index],
                         'shares': row[share_index]},
                        synchronize_session=False)
                    db.session.commit()
                if not_updated_ac_ids:
                    msg = ', '.join(not_updated_ac_ids)
                    c_abort(
                        422, message='following account ids not found: ' + msg)
            os.remove(path)
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Updated Accounts'}, 200


class AccountBulkCreateApi(AuthResource):
    """
        insert accounts , management profiles
    """

    invalid_list = [
        '#n/a', '#n.a', 'n.a', 'n/a', '#calc', '#N/A', 'NULL',
        '--', '42', 42]
    def _get_clean_data(self, val, default=None):
        if str(val) in self.invalid_list:
            return default
        return str(val)


    @role_permission_required(perms=[ROLE.EPT_AA], roles=[ROLE.ERT_SU])
    def post(self):
        try:
            data = request.form
            inserted = 0
            if "domain_id" not in data:
                return c_abort(422, message="domain_id is mandatory.")
            domain_id = data["domain_id"]
            if "filename" not in request.files:
                return c_abort(422, message="file is mandatory.")
            file = request.files['filename']
            if '.xls' not in file.filename:
                return c_abort(422, message="only xls/xlsx file is allowed.")
            if "account_type" not in data:
                return c_abort(422, message="account_type is mandatory.")
            account_type = data["account_type"]
            folder_name = uuid.uuid4().hex
            upload_path = os.path.join(
                current_app.config['BASE_UPLOADS_FOLDER'],
                'account_bulk_file', folder_name)
            if not os.path.exists(upload_path):
                os.makedirs(upload_path)
            industry_sector_by_id = {}
            industries = Industry.query.all()
            for industry in industries:
                industry_sector_by_id[industry.name.lower()] = \
                    {'sector_id': industry.sector_id,
                     'industry_id': industry.row_id}
            path = os.path.join(upload_path, file.filename)
            file.save(path)
            file_wb = open_workbook(path)
            sheet = file_wb.sheets()[0]
            rows = sheet.nrows
            accounts_to_create = []
            account_name_list = []
            duplicate_rows = []
            for row in range(1, rows):
                isin_number = self._get_clean_data(sheet.cell(row, 1).value, None)
                sedol = self._get_clean_data(sheet.cell(row, 2).value, None)
                account_name = self._get_clean_data(sheet.cell(row, 4).value, None)
                if not all([sedol, isin_number, account_name]):
                    c_abort(422, message="sedol, isin_number and name are mandatory."
                                         " Row {} failed.".format(row + 1))
                account = Account.query.filter(
                        func.lower(Account.account_name) == account_name.lower()
                    ).first()
                if account:
                    continue
                if account_name.lower() in account_name_list:
                    duplicate_rows.append({
                        "row_number": row + 1,
                        'isin_number': isin_number,
                        "sedol": sedol,
                        "account_name": account_name,
                        "identifier": sheet.cell(row, 0).value,
                        "perm_security_id": sheet.cell(row, 3).value,
                        "fsym_id": sheet.cell(row, 30).value,
                        "nse_symbol": sheet.cell(row, 31).value,
                        "website": sheet.cell(row, 13).value,
                        "country": sheet.cell(row, 8).value,
                        "region": sheet.cell(row, 7).value,
                        "address_state": sheet.cell(row, 9).value,
                        "address_city": sheet.cell(row, 10).value,
                        "address_street_one": sheet.cell(row, 11).value,
                        "address_country": sheet.cell(row, 8).value,
                        "description": sheet.cell(row, 12).value,
                        "phone_primary": sheet.cell(row, 14).value
                    })
                data = {
                    "isin_number": isin_number,
                    "sedol": sedol,
                    "account_name": account_name,
                    "identifier": sheet.cell(row, 0).value,
                    "perm_security_id": sheet.cell(row, 3).value,
                    "fsym_id": sheet.cell(row, 30).value,
                    "nse_symbol": sheet.cell(row, 31).value,
                    "website": sheet.cell(row, 13).value,
                    "account_type": account_type,
                    "domain_id": domain_id,
                    "profile": {
                        "country": sheet.cell(row, 8).value,
                        "region": sheet.cell(row, 7).value,
                        "address_state": sheet.cell(row, 9).value,
                        "address_city": sheet.cell(row, 10).value,
                        "address_street_one": sheet.cell(row, 11).value,
                        "address_country": sheet.cell(row, 8).value,
                        "description": sheet.cell(row, 12).value,
                        "phone_primary": sheet.cell(row, 14).value,
                    }
                }
                account_name_list.append(account_name.lower())
                industry = self._get_clean_data(sheet.cell(row, 5).value, None)
                try:
                    if industry and industry.lower() in industry_sector_by_id:
                        data['profile']['sector_id'] = industry_sector_by_id[
                            industry.lower()]['sector_id']
                        data['profile']['industry_id'] = industry_sector_by_id[
                            industry.lower()]['industry_id']
                except Exception as e:
                    pass
                mngt_cnt = 0
                managements = []
                start = 15
                for i in range(5):
                    name = self._get_clean_data(sheet.cell(row, start).value, "")
                    designation = self._get_clean_data(
                        sheet.cell(row, start + 1).value, "")
                    email = self._get_clean_data(
                        sheet.cell(row, start + 2).value, "")
                    start += 3
                    mngt_cnt += 1
                    if name and mngt_cnt:
                        managements.append(
                            {'name': name, 'sequence_id': mngt_cnt,
                            'designation': designation,
                            'email': email})

                if managements:
                    data['profile']['management_profiles'] = managements

                accounts_to_create.append(data)
            if duplicate_rows:
                c_abort(422, message="duplicate data.", errors=duplicate_rows)
            if accounts_to_create:
                data, errors = AccountSchema(many=True).load(accounts_to_create)
                if errors:
                    c_abort(422, message="Invalid data.", errors=errors[0])
                for account in data:
                    account.created_by = g.current_user['row_id']
                    account.updated_by = g.current_user['row_id']
                    account.profile.account_type = account_type
                    account.stats = AccountStats()
                    account.settings = AccountSettings()

                db.session.add_all(data)
                db.session.commit()
                inserted = len(data)
        except IntegrityError as e:
            print(e)
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (lower(account_name::text))=(abc) already exists.
                column = e.orig.diag.message_detail.split('(')[2].split(':')[0]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # DETAIL: Key(manager_id) = (4) is not present in table "user".
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
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
        return {'message': "{} Account(s) created.".format(inserted) }, 201
