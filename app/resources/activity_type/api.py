"""
API endpoints for "admin activity-type" package.
"""
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

from app import db, c_abort
from app.resources.roles.models import ROLE
from app.base.api import AuthResource
from app.base import constants as APP
from app.auth.decorators import role_permission_required
from app.resources.activity_type.models import ActivityType
from app.resources.activity_type.schemas import (
    ActivityTypeSchema,
    ActivityTypeReadArgsSchema)


class ActivityTypeAPI(AuthResource):
    """
    Create, update, delete API for accounts
    """

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[ROLE.ERT_SU])
    def post(self):
        """
        Create an Activity Type
        """
        activity_type_schema = ActivityTypeSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = activity_type_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by

            db.session.add(data)
            db.session.commit()
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

        return {'message': 'Activity Type added: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    def put(self, row_id):
        """
        Update an account
        """
        activity_type_schema = ActivityTypeSchema()
        # first find model
        model = None
        try:
            model = ActivityType.query.get(row_id)
            if model is None:
                c_abort(404, message='Activity Type id: %s'
                        ' does not exist' % str(row_id))
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
            data, errors = activity_type_schema.load(
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
                # format of the message:
                # Key (country_id, state_id, city_name)=(1, 1, Hyd)
                # already exists.
                column = e.orig.diag.message_detail.split('(')[2].split(':')[0]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (country_id)=(2) is not present in table "country".
                # Key (state_id)=(3) is not present in table "state".
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
        return {'message': 'Updated Activity Type id: %s' % str(row_id)}, 200

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[ROLE.ERT_SU])
    def delete(self, row_id):
        """
        Delete an account
        """
        model = None
        account_user = None
        try:
            # first find model
            model = ActivityType.query.get(row_id)
            if model is None :
                c_abort(404, message='Activity Type id: %s'
                        ' does not exist' % str(row_id))
            
            model.deleted = True
            model.updated_by = g.current_user['row_id']
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

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    def get(self, row_id):
        """
        Get an city by id
        """
        model = None
        try:
            # first find model
            model = ActivityType.query.get(row_id)
            if model is None:
                c_abort(404, message='Activity Type id: %s does not exist' %
                                     str(row_id))
            result = ActivityTypeSchema().dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class ActivityTypeListAPI(AuthResource):
    """
    Read API for Activity Type lists, i.e, more than 1 city
    """
    model_class = ActivityType

    def __init__(self, *args, **kwargs):
        super(ActivityTypeListAPI, self).__init__(*args, **kwargs)

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

        query_filters['base'].append(ActivityType.is_active==True)

        query = self._build_final_query(query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    def get(self):
        """
        Get the list
        """
        activity_type_read_schema = ActivityTypeReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            activity_type_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(ActivityType), operator)
            # making a copy of the main output schema
            activity_type_schema = ActivityTypeSchema(
                exclude=ActivityTypeSchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                activity_type_schema = ActivityTypeSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching Activity Type found')
            result = activity_type_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200