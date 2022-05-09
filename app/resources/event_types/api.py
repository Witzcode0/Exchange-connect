"""
API endpoints for "event types" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from sqlalchemy.exc import IntegrityError
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.orm import load_only
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.base import constants as APP
from app.auth.decorators import role_permission_required
from app.resources.roles import constants as ROLE
from app.resources.event_types.models import EventType
from app.resources.event_types.schemas import (
    EventTypeSchema, EventTypeReadArgsSchema)


# main input and output schema
event_type_schema = EventTypeSchema()
# schema for reading get arguments
event_type_read_schema = EventTypeReadArgsSchema(strict=True)


class EventTypeAPI(AuthResource):
    """
    Create, update, delete API for event types
    """

    @role_permission_required(perms=[ROLE.EPT_AA])
    @swag_from('swagger_docs/event_type_post.yml')
    def post(self):
        """
        Create an event type
        """
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = event_type_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            data.created_by = g.current_user['row_id']
            data.account_id = g.current_user['account_id']
            data.updated_by = data.created_by
            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
        except HTTPException as e:
            raise e
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (name)=(Webinar) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Event Type created: %s' %
                           str(data.row_id), 'row_id': data.row_id}, 201

    @role_permission_required(perms=[ROLE.EPT_CR])
    @swag_from('swagger_docs/event_type_put.yml')
    def put(self, row_id):
        """
        Update a event type by id
        """
        # first find model
        model = None
        try:
            model = EventType.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Event type id: %s does not exist' %
                                     str(row_id))
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
            data, errors = event_type_schema.load(
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
                # Key (name)=(Webinar) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
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
        return {'message': 'Updated Event Type id: %s' % str(row_id)}, 200

    @role_permission_required(perms=[ROLE.EPT_CR])
    @swag_from('swagger_docs/event_type_delete.yml')
    def delete(self, row_id):
        """
        Delete a event type by id
        """
        model = None
        try:
            # first find model
            model = EventType.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Event Type id: %s does not exist' %
                                     str(row_id))
            # if model is found, and not yet deleted, delete it
            model.deleted = True
            db.session.add(model)
            db.session.commit()
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204

    @role_permission_required(perms=[ROLE.EPT_AR])
    @swag_from('swagger_docs/event_type_get.yml')
    def get(self, row_id):
        """
        Get a event type by id
        """
        model = None
        try:
            # first find model
            model = EventType.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Event Type id: %s does not exist' %
                                     str(row_id))
            result = event_type_schema.dump(model)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class EventTypeListAPI(AuthResource):
    """
    Read API for event type lists, i.e, more than 1 event type
    """
    model_class = EventType

    def __init__(self, *args, **kwargs):
        super(EventTypeListAPI, self).__init__(*args, **kwargs)

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

    @swag_from('swagger_docs/event_type_get_list.yml')
    def get(self):
        """
        Get the list
        """
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            event_type_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(EventType), operator)
            # making a copy of the main output schema
            event_type_schema = EventTypeSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                event_type_schema = EventTypeSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching event types found')
            result = event_type_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
