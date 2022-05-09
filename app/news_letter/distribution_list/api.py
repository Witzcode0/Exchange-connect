"""
API endpoints for "Distribution List API" package.
"""
import os
import pandas as pd
import numpy as np

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.orm import load_only, joinedload
from sqlalchemy import Date, cast, func
from sqlalchemy.exc import IntegrityError
from marshmallow.exceptions import ValidationError
from app.base.api import AuthResource, BaseResource, load_current_user

from app.base import constants as APP
from app import db, c_abort, distributionlistfile
from app.base.api import AuthResource
from app.auth.decorators import role_permission_required
from app.resources.roles import constants as ROLE
from app.common.helpers import save_files_locally
from app.resources.users.models import User
from app.news_letter.distribution_list.models import (
    DistributionList)
from app.news_letter.distribution_list.schemas import (
    DistributionListSchema, DistributionListReadArgsSchema)
from app.resources.accounts.models import Account
from app.news_letter.distribution_list import constants as DSTR
from app.resources.unsubscriptions.helpers import create_default_unsubscription
from app.resources.unsubscriptions.models import Unsubscription
from app.resources.unsubscriptions.schemas import UnsubscriptionSchema


class DistributionListFrontEndAPI(BaseResource):
    """
    For creating distribution list 
    """

    def post(self):
        """
        Create distribution list
        """
        distribution_list_schema = DistributionListSchema()
        json_data = request.get_json()
        # get the form data from the request
        if not json_data:
            c_abort(400)

        try:
            data, errors = distribution_list_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            # check with user
            if 'email' in json_data and json_data['email']:
                user = User.query.filter(User.email == json_data['email']).all()
                if user:
                    c_abort(422, message="User already exist with mentioned email", errors={
                    "email_id": ["User already exist with mentioned email"]})

            # no errors, so add data to db
            # if g.current_user['row_id']:
            #     data.created_by = g.current_user['row_id']
            #     data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()

            # add default unsubscription record
            create_default_unsubscription(data.email)

        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
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

        return {'message': 'Distribution user Created: %s' %
                           str(data.row_id), 'row_id': data.row_id}, 201


class DistributionListAPI(AuthResource):
    """
    for edit, delete and get distribution list
    """
    def post(self):
        """
        Create distribution list
        """
        distribution_list_schema = DistributionListSchema()
        json_data = request.get_json()
        # get the form data from the request
        if not json_data:
            c_abort(400)

        try:
            data, errors = distribution_list_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            #check with user
            if 'email' in json_data and json_data['email']:
                user = User.query.filter(User.email == json_data['email']).all()
                if user:
                    c_abort(422, message="User already exist with mentioned email", errors={
                    "email_id": ["User already exist with mentioned email"]})
                    raise ValidationError("Already user exist with mentioned EmailID")

            # no errors, so add data to db
            if g.current_user['row_id']:
                data.created_by = g.current_user['row_id']
                data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()

            # add default unsubscription record
            create_default_unsubscription(data.email)

        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
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

        return {'message': 'Distribution user Created: %s' %
                           str(data.row_id), 'row_id': data.row_id}, 201

    def put(self, row_id):
        """
        Update distribution list
        """
        distribution_list_schema = DistributionListSchema()
        unsubscription_schema = UnsubscriptionSchema()

        model = None
        try:
            model = DistributionList.query.get(row_id)
            if model is None:
                c_abort(404, message='Distribution user id: %s'
                                     ' does not exist' % str(row_id))
        except Forbidden as e:
            raise e
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
            if not Unsubscription.query.filter(
                Unsubscription.email == json_data['email']).first():
                create_default_unsubscription(json_data['email'])
            unsubscriptions = None
            if 'unsubscribe_newsletter' in json_data:
                unsubscriptions = json_data.pop('unsubscribe_newsletter')

            if unsubscriptions:
                unsubscription_data, errors = unsubscription_schema.load(
                    {'events':["news_letter"]}, instance=model.unsubscriptions,
                    partial=True)
                if errors:
                    c_abort(422, errors=errors)
            else:
                unsubscription_data, errors = unsubscription_schema.load(
                    {'events':[]}, instance=model.unsubscriptions,
                    partial=True)
                if errors:
                    c_abort(422, errors=errors)

            data, errors = distribution_list_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()

        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
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

        return {'message': 'Update Distribution user id: %s' %
                           str(row_id)}, 200

    def delete(self, row_id):
        """
        Delete a distribution list
        """
        model = None
        try:
            # first find model
            model = DistributionList.query.get(row_id)
            if model is None:
                c_abort(404, message='Distribution user id: %s'
                        ' does not exist' % str(row_id))

            email = model.email
            # if model is found, and not yet deleted, delete it
            db.session.delete(model)

            unsub_model = Unsubscription.query.filter(
                Unsubscription.email == email).first()
            db.session.delete(unsub_model)
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

    def get(self, row_id):
        """
        Get a distribution list request by id
        """
        model = None
        try:
            # first find model
            model = DistributionList.query.join(
                Unsubscription, Unsubscription.email == DistributionList.email,
                isouter=True).filter(DistributionList.row_id == row_id).first()
            if model is None:
                c_abort(404, message='Distribution user id: %s'
                                     ' does not exist' % str(row_id))
            result = DistributionListSchema().dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class DistributionListofListAPI(AuthResource):
    """
    Read API for distribution list, i.e, more than 1
    """
    model_class = DistributionList

    def __init__(self, *args, **kwargs):
        super(DistributionListofListAPI, self).__init__(*args, **kwargs)

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

        innerjoin = False
        main_filter = None
        # build specific extra queries filters
        account_name = None
        full_name = None

        if extra_query:
            if "started_at_from" in extra_query and extra_query['started_at_from']:
                started_at = extra_query.pop('started_at_from')
                query_filters['filters'].append(
                    func.cast(DistributionList.created_date,Date) >= started_at)
            if "ended_at_to" in extra_query and extra_query['ended_at_to']:
                ended_to = extra_query.pop('ended_at_to')
                query_filters['filters'].append(
                    func.cast(DistributionList.created_date,Date) <= ended_to)
            if 'account_name' in extra_query and extra_query['account_name']:
                account_name = '%' + extra_query.pop('account_name') + '%'
                query_filters['filters'].append(
                func.lower(Account.account_name).like(func.lower(account_name)))
            if 'full_name' in extra_query and extra_query['full_name']:
                full_name = '%' + (extra_query["full_name"]).lower() + '%'
                query_filters['filters'].append(func.concat(
                    func.lower(DistributionList.first_name), ' ',
                    func.lower(DistributionList.last_name)).like(full_name))
            if 'main_filter' in extra_query and extra_query['main_filter']:
                main_filter = extra_query['main_filter']
                if main_filter == DSTR.DSTR_SUB:
                    ''' query for user subscribe by their own'''
                    query_filters['filters'].append(DistributionList.created_by == None)

                elif main_filter == DSTR.DSTR_ADMIN:
                    ''' query for user subscribed by admin'''
                    query_filters['filters'].append(DistributionList.created_by != None)

        query = self._build_final_query(
            query_filters, query_session, operator)


        final_query = query.options(
            joinedload(DistributionList.creator).load_only(
                'row_id', 'account_id').joinedload(
                User.account).joinedload(Account.profile))

        final_query = final_query.join(Account, Account.row_id == DistributionList.account_id)

        return final_query, db_projection, s_projection, order, paging

    def get(self):
        """
        Get the list
        """
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            DistributionListReadArgsSchema())

        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(DistributionList),
                                 operator)

            # making a copy of the main output schema
            comment_schema = DistributionListSchema(
                exclude=DistributionListSchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                comment_schema = DistributionListSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching Distribution user found')
            result = comment_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class DistributionListXLSAPI(AuthResource):
    """
    For creating new distribution list by xml file
    """

    # @role_permission_required(perms=[ROLE.EPT_AA])
    def post(self):
        """
        Create distribution list 
        """
        all_errors = {}
        try:
            # create list of Distribution user from xls file
            fpath, fname, ferrors = save_files_locally(
                distributionlistfile, request.files['filename'])
            if ferrors:
                return ferrors
            user_df = pd.read_excel(fpath)
            user_df.keys().str.strip()
            # rename dataframe column as per schema fields
            user_df.rename(columns={
                'Company name': 'account_id',
                'Email Address': 'email',
                'First Name': 'first_name',
                'Last Name': 'last_name',
                'Contact No.': 'contact_number',
                'Designation': 'designation',
            }, inplace=True)
            for j in range(len(user_df)):
                try:
                    distribution_dict = {}
                    for i in user_df.keys():
                        # create dict 
                        if i == "account_id":
                            str_data = Account.query.filter(func.lower(
                                Account.account_name) == func.lower(
                                user_df[i][j])).first()
                            if str_data:
                                str_data = str_data.row_id
                            else:
                                continue
                        else:
                            str_data = str(user_df[i][j]) if (
                                str(user_df[i][j]) not in ['nan',None]) else ""
                        distribution_dict[i] = str_data
                    # load dict into schema
                    data, errors = DistributionListSchema().load(
                        distribution_dict)
                    if errors:
                        continue
                    if 'email' in distribution_dict and distribution_dict['email']:
                        user = User.query.filter(User.email == distribution_dict['email']).all()
                        if user:
                            continue
                    data.created_by = g.current_user['row_id']
                    data.updated_by = data.created_by

                    db.session.add(data)
                    db.session.commit()

                    # add default unsubscription record
                    create_default_unsubscription(data.email)

                except IntegrityError as e:
                    db.session.rollback()
                    if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                        column = e.orig.diag.message_detail.split('(')[1][:-2]

                    if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                        column = e.orig.diag.message_detail.split('(')[1][:-2]
                    # for any other unknown db errors
                    current_app.logger.exception(e)
                    continue

        except HTTPException as e:
            raise e

        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Distribution List created'}, 201


class DistributionBulkAPI(AuthResource):
    """
    For update bulk Distribution user

    """

    def put(self):
        """
        Update Corporate announcement by admin
        """
        distribution_schema = DistributionListSchema()
        unsubscription_schema = UnsubscriptionSchema()
        model = None

        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)
        if not json_data["users"]:
            c_abort(422,message='Distribution users not exist')
        users_list = json_data["users"]
        try:
            # TODO :-- Apply schema for announcement list
            for user in users_list:

                if  "row_id" in user.keys():
                    model = DistributionList.query.get(user["row_id"])
                    if model is None:
                        c_abort(404, message='Distribution user id: %s'
                                             ' does not exist' % str(user["row_id"]))
                    if not Unsubscription.query.filter(
                        Unsubscription.email == user['email']).first():
                        create_default_unsubscription(user['email'])
                    unsubscriptions = None
                    if 'unsubscribe_newsletter' in user:
                        unsubscriptions = user.pop('unsubscribe_newsletter')

                    if unsubscriptions:
                        unsubscription_data, errors = unsubscription_schema.load(
                            {'events':["news_letter"]}, instance=model.unsubscriptions,
                            partial=True)
                        if errors:
                            c_abort(422, errors=errors)
                    else:
                        unsubscription_data, errors = unsubscription_schema.load(
                            {'events':[]}, instance=model.unsubscriptions,
                            partial=True)
                        if errors:
                            c_abort(422, errors=errors)

                    data, errors = distribution_schema.load(
                        user, instance=model, partial=True)
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

        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Distribution users are updated'}, 200


class DistributionBulkDeletAPI(AuthResource):
    """
    For Delete bulk Distribution user

    """

    def put(self):

        model = None

        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)
        if not json_data["users"]:
            c_abort(422,message='Distribution users not exist')
        users_list = json_data["users"]
        try:
            for user_id in users_list:
            # first find model
                model = DistributionList.query.get(user_id)
                if model is None:
                    c_abort(404, message='Distribution user id: %s'
                            ' does not exist' % str(user_id))
                # if model is found, and not yet deleted, delete it
                email = model.email

                db.session.delete(model)

                unsub_model = Unsubscription.query.filter(
                    Unsubscription.email == email).first()
                db.session.delete(unsub_model)

                db.session.commit()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Distribution users are Deleted'}, 200
