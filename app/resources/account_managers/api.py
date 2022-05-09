"""
API endpoints for "account manager" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.base import constants as APP
from app.auth.decorators import role_permission_required
from app.resources.account_managers.models import (
    AccountManager, AccountManagerHistory)
from app.resources.account_managers.schemas import (
    AccountManagerSchema, AccountManagerReadArgsSchema)
from app.resources.roles import constants as ROLE


class AccountManagerAPI(AuthResource):
    """
    Create, update, delete API for account manager
    """

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[ROLE.ERT_SU])
    def post(self):
        """
        Create an account manager
        """
        account_manager_schema = AccountManagerSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            model = None
            data, errors = account_manager_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # if account_id already exists then store in history table
            model = AccountManager.query.filter(
                AccountManager.account_id == data.account_id).first()

            if model:
                account_manager_history = AccountManagerHistory(
                    account_id=model.account_id,
                    manager_id=model.manager_id,
                    created_by=model.created_by,
                    updated_by=g.current_user['row_id'])
                db.session.add(account_manager_history)
                # delete old account manager
                db.session.delete(model)
                db.session.commit()

            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # DETAIL: Key(account_id) = (22521) already exists.
                column = e.orig.diag.message_detail.split('(')[1].split(')')[0]
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
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Account manager added: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[ROLE.ERT_SU])
    def delete(self, row_id):
        """
        Delete an account manager
        """
        model = None
        try:
            # first find model
            model = AccountManager.query.get(row_id)
            if model is None:
                c_abort(404, message='Account Manager id: %s'
                        ' does not exist' % str(row_id))
            # first data insert into history table
            account_manager_history = AccountManagerHistory(
                account_id=model.account_id, manager_id=model.manager_id,
                created_by=model.created_by,
                updated_by=g.current_user['row_id'])
            db.session.add(account_manager_history)
            # if model is found, and not yet deleted, delete it
            db.session.delete(model)
            db.session.commit()
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[ROLE.ERT_SU])
    def get(self, row_id):
        """
        Get an account manager by id
        """
        model = None
        try:
            # first find model
            model = AccountManager.query.get(row_id)
            if model is None:
                c_abort(404, message='Account Manager id: %s'
                        ' does not exist' % str(row_id))
            result = AccountManagerSchema().dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class AccountManagerList(AuthResource):
    """
    Read API for account manager lists, i.e, more than 1 account
    """
    model_class = AccountManager

    def __init__(self, *args, **kwargs):
        super(AccountManagerList, self).__init__(*args, **kwargs)

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

        query = self._build_final_query(query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[ROLE.ERT_SU])
    def get(self):
        """
        Get the list
        """
        account_manager_read_schema = AccountManagerReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            account_manager_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(AccountManager), operator)
            # making a copy of the main output schema
            account_manager_schema = AccountManagerSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                account_manager_schema = AccountManagerSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching account manager found')
            result = account_manager_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data, 'total': total}, 200
