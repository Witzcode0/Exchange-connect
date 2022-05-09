"""
API endpoints for "event requests" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_
from sqlalchemy.orm import load_only
from flasgger.utils import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.resources.event_invites import constants as EVENT_INVITE
from app.resources.event_invites.models import EventInvite
from app.resources.event_invites.schemas import (
    EventInviteSchema, EventInviteReadArgsSchema)
from app.resources.events.models import Event
from app.resources.event_requests.schemas import (
    OpenEventJoinSchema, EventRequestReadArgsSchema,
    BulkEventInviteStatusChangeSchema)
from app.base import constants as APP

from queueapp.event_tasks import manage_events_counts_and_avg_rating


# main input and output schema
event_invite_schema = EventInviteSchema()
# schema for reading get arguments
event_invite_read_schema = EventRequestReadArgsSchema(strict=True)
# schema for open event invite
open_event_join_schema = OpenEventJoinSchema()


class EventRequestAPI(AuthResource):
    """
    For creating new event requests
    """
    @swag_from('swagger_docs/event_request_post.yml')
    def post(self):
        """
        Create an event request
        """
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = event_invite_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            if data.status != EVENT_INVITE.REQUESTED:
                abort(403)

            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()

        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (email)=(example@example.com) already exists.
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

        return {'message': 'Event Request created: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201

    @swag_from('swagger_docs/event_request_get.yml')
    def get(self, row_id):
        """
        Get a registration request by id
        """
        model = None
        try:
            # first find model
            model = EventInvite.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Event id: %s'
                        ' does not exist' % str(row_id))
            model.participated = 10
            result = event_invite_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200

    @swag_from('swagger_docs/event_request_put.yml')
    def put(self, row_id):
        """
        Update an event
        """
        # first find model
        model = None
        try:
            model = EventInvite.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Event Request id: %s'
                        ' does not exist' % str(row_id))
            if (model.user_id != g.current_user['row_id'] or
                    model.created_by != g.current_user['row_id']):
                abort(403)
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
            # validate and deserialize input
            data, errors = event_invite_schema.load(
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
        return {'message': 'Updated Event Request id: %s' %
                str(row_id)}, 200

    @swag_from('swagger_docs/event_request_delete.yml')
    def delete(self, row_id):
        """
        Delete an event Request
        """
        model = None
        try:
            # first find model
            model = EventInvite.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Event Request id: %s'
                        ' does not exist' % str(row_id))
            if model.created_by != g.current_user['row_id']:
                abort(403)
            # if model is found, and not yet deleted, delete it
            model.updated_by = g.current_user['row_id']
            model.deleted = True
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


class EventRequestsListAPI(AuthResource):
    """
    Read API for event lists, i.e, more than
    1 event
    """
    model_class = EventInvite

    def __init__(self, *args, **kwargs):
        super(EventRequestsListAPI, self).__init__(*args, **kwargs)

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

        query_filters['base'].append(
            EventInvite.status == EVENT_INVITE.REQUESTED)

        query = self._build_final_query(query_filters, query_session, operator)
        query = query.join(Event, and_(
            Event.row_id == EventInvite.event_id,
            Event.created_by == g.current_user['row_id']))

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/event_request_get_list.yml')
    def get(self):
        """
        Get the list
        """
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            event_invite_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(EventInvite),
                                 operator)
            # making a copy of the main output schema
            event_invite_schema = EventInviteSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                event_invite_schema = EventInviteSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching Event Requests found')
            result = event_invite_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class OpenEventJoinAPI(AuthResource):
    """
    For directly joining open events
    """

    @swag_from('swagger_docs/open_event_join_post.yml')
    def post(self):
        """
        Create an event invite (sort of like self invite!)
        """
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = open_event_join_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            if open_event_join_schema._cached_event.open_to_all:
                status = EVENT_INVITE.REQUESTED
            elif open_event_join_schema._cached_event.public_event:
                status = EVENT_INVITE.ACCEPTED
            # no errors, so add data to db
            event_invite_data = EventInvite(
                event_id=data['event_id'],
                user_id=g.current_user['row_id'],
                status=status,
                created_by=g.current_user['row_id'],
                updated_by=g.current_user['row_id'])
            db.session.add(event_invite_data)
            db.session.commit()
            # for update event counts and avg_rating
            manage_events_counts_and_avg_rating.s(
                True, data['event_id']).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (event_id, user_id)=(2, 2) already exists.
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

        return {'message': 'Open event joined, join id: %s' %
                str(event_invite_data.row_id),
                'row_id': event_invite_data.row_id}, 201


class BulkEventInviteStatusChangeAPI(AuthResource):
    """
    Bulk changes of event invite status into invited for user
    of particular event by event creator
    """
    @swag_from('swagger_docs/bulk_event_status_change.yml')
    def put(self, event_id):
        """
        change event invite status into invited users
        which are requested particular event
        :return:
        """
        model = None
        try:
            model = Event.query.get(event_id)
            if model is None or model.deleted:
                c_abort(404, message='Event id: %s'
                                     ' does not exist' % str(event_id))
            if model.created_by != g.current_user['row_id']:
                abort(403)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            data, errors = BulkEventInviteStatusChangeSchema().load(json_data)
            if errors:
                c_abort(422, errors=errors)

            if 'invite_ids' in data and data['invite_ids']:
                EventInvite.query.filter(and_(
                    EventInvite.event_id == event_id,
                    EventInvite.status == EVENT_INVITE.REQUESTED,
                    EventInvite.row_id.in_(data['invite_ids']))).update({
                        EventInvite.status: EVENT_INVITE.ACCEPTED},
                        synchronize_session=False)
                db.session.commit()
                # for update event counts and avg_rating
                manage_events_counts_and_avg_rating.s(
                    True, event_id).delay()
            elif 'event_invites' in data and data['event_invites']:
                for event_invite in data['event_invites']:
                    EventInvite.query.filter(and_(
                        EventInvite.event_id == event_id,
                        EventInvite.user_id == event_invite.user_id)).update({
                            EventInvite.status: EVENT_INVITE.ATTENDED,
                            EventInvite.comment: event_invite.comment})
                    db.session.commit()
                # for update event counts and avg_rating
                manage_events_counts_and_avg_rating.s(
                    True, event_id).delay()

        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Updated Event id: %s' % str(event_id)}, 200
