"""
API endpoints for "reference event types" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from flasgger.utils import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.base import constants as APP
from app.corporate_access_resources.ref_event_types.models import \
    CARefEventType
from app.corporate_access_resources.ref_event_types.schemas import (
    CARefEventTypeSchema, CARefEventTypeReadArgsSchema)
from app.corporate_access_resources.corporate_access_events.models import \
    CorporateAccessEvent


class CARefEventTypeAPI(AuthResource):
    """
    CRUD API for managing reference event types
    """
    @swag_from('swagger_docs/corporate_ref_event_types_post.yml')
    def post(self):
        """
        Create a reference event type
        """
        corporate_ref_event_type_schema = CARefEventTypeSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = corporate_ref_event_type_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (name)=(conference) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            elif APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (account_id)=(3) is not present in table "account".
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

        return {'message': 'Corporate Access Reference Event Type added: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201

    @swag_from('swagger_docs/corporate_ref_event_types_put.yml')
    def put(self, row_id):
        """
        Update a reference event type
        """
        corporate_ref_event_type_schema = CARefEventTypeSchema()
        # first find model
        model = None
        try:
            model = CARefEventType.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Corporate Access Reference Event '
                        'Type id: %s does not exist' % str(row_id))
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
            data, errors = corporate_ref_event_type_schema.load(
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
                # Key (name)=(conference) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            elif APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (account_id)=(3) is not present in table "account".
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
        return {'message': 'Updated Corporate Access Reference Event '
                'Type id: %s' % str(row_id)}, 200

    @swag_from('swagger_docs/corporate_ref_event_types_delete.yml')
    def delete(self, row_id):
        """
        Delete a reference event type
        """
        model = None
        event_type = None
        try:
            # first find model
            model = CARefEventType.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Corporate Access Reference Event '
                        'Type id: %s does not exist' % str(row_id))
            # check particular sub-type is used in event or not
            event_type = CorporateAccessEvent.query.filter(
                CorporateAccessEvent.event_type_id == row_id).first()
            if event_type:
                c_abort(422, message=APP.MSG_REF_OTHER_TABLE +
                        ' CorporateAccessEvent', errors={'row_id': [
                            APP.MSG_REF_OTHER_TABLE + ' CorporateAccessEvent']}
                        )
            # using soft delete
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

    @swag_from('swagger_docs/corporate_ref_event_types_get.yml')
    def get(self, row_id):
        """
        Get a reference event type by id
        """
        corporate_ref_event_type_schema = CARefEventTypeSchema(
            exclude=CARefEventTypeSchema._default_exclude_fields)
        model = None
        try:
            # first find model
            model = CARefEventType.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Corporate Access Reference Event '
                        'Type id: %s does not exist' % str(row_id))
            result = corporate_ref_event_type_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class CARefEventTypeListAPI(AuthResource):
    """
    Read API for reference event type lists, i.e, more than 1 event
    """
    model_class = CARefEventType

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['creator', 'account']
        super(CARefEventTypeListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        query_filters, extra_query, db_evention, s_evention, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)
        # build specific extra queries filters
        if extra_query:
            pass

        query = self._build_final_query(query_filters, query_session, operator)

        return query, db_evention, s_evention, order, paging

    @swag_from('swagger_docs/corporate_ref_event_types_get_list.yml')
    def get(self):
        """
        Get the list
        """
        corporate_ref_event_type_read_schema = CARefEventTypeReadArgsSchema(
            strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            corporate_ref_event_type_read_schema)
        try:
            # build the sql query
            query, db_evention, s_evention, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(CARefEventType), operator)
            # making a copy of the main output schema
            corporate_ref_event_type_schema = CARefEventTypeSchema(
                exclude=CARefEventTypeSchema._default_exclude_fields)
            if db_evention:
                # change the query to include only requested fields
                query = query.options(load_only(*db_evention))
            if s_evention:
                # change the schema to include only requested fields
                corporate_ref_event_type_schema = CARefEventTypeSchema(
                    only=s_evention)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching corporate access '
                        'reference event types found')
            result = corporate_ref_event_type_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
