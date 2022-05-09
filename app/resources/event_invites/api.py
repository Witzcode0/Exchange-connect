"""
API endpoints for "event invites" package.
"""

import datetime

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from flasgger.utils import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.resources.event_invites import constants as EVENT_INVITE
from app.resources.event_invites.models import EventInvite
from app.resources.roles import constants as ROLE
from app.resources.event_invites.schemas import (
    EventInviteSchema, EventInviteReadArgsSchema)
from app.resources.events.schemas import EventSchema
from app.resources.events.models import Event
from app.resources.event_invites.helpers import calculate_avg_rating
from app.base import constants as APP
from app.resources.notifications import constants as NOTIFY

from queueapp.event_tasks import manage_events_counts_and_avg_rating
from queueapp.notification_tasks import add_event_creator_notification

event_schema = EventSchema()
# main input and output schema
event_invite_schema = EventInviteSchema()
# schema for reading get arguments
event_invite_read_schema = EventInviteReadArgsSchema(strict=True)


class EventInviteAPI(AuthResource):
    """
    For creating new event invites
    """
    @swag_from('swagger_docs/event_invite_post.yml')
    def post(self):
        """
        Create an event
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
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            if json_data['participants']:
                for user_id in json_data['participants']:
                    data.user_id = user_id
                    try:
                        db.session.add(data)
                        db.session.commit()
                    except IntegrityError as e:
                        db.session.rollback()
                        print("User id for this event invite exists", user_id)

            else:
                db.session.add(data)
                db.session.commit()

        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (event_id, user_id)=(2, 2) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (event_id)=(9) is not present in table "event".
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

        return {'message': 'Event Invite created: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201

    @swag_from('swagger_docs/event_invite_get.yml')
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
            # event_model = Event.query.filter_by(
            # row_id=model.event_id).first()
            # model.event = event_model
            result = event_invite_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200

    @swag_from('swagger_docs/event_invite_put.yml')
    def put(self, row_id):
        """
        Update an event
        """
        # first find model
        model = None
        try:
            model = EventInvite.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Event Invite id: %s'
                        ' does not exist' % str(row_id))

            if (model.user_id != g.current_user['row_id'] and
                    model.created_by != g.current_user['row_id'] and
                    ROLE.EPT_NU not in g.current_user['role']['permissions']):
                abort(403)
            model_status = model.status
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
            if 'rating' in json_data and json_data['rating']:
                if (model.event.created_by == g.current_user['row_id'] or
                        model.user_id != g.current_user['row_id'] or
                        model.status != EVENT_INVITE.ACCEPTED or
                        model.event.end_date.date() >
                        datetime.datetime.utcnow().date()):
                    json_data.pop('rating')

            data, errors = event_invite_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()

            # for update event counts and avg_rating
            if (('status' in json_data and json_data['status']) or
                    ('rating' in json_data and (
                        json_data['rating'] or json_data['rating'] == 0))):
                manage_events_counts_and_avg_rating.s(
                    True, model.event_id).delay()
            if 'status' in json_data:
                if json_data['status'] == EVENT_INVITE.ACCEPTED:
                    sub_type = NOTIFY.NT_EVENT_REQ_ACCEPTED
                elif json_data['status'] == EVENT_INVITE.REJECTED:
                    sub_type = NOTIFY.NT_EVENT_REQ_REJECTED
                elif json_data['status'] == EVENT_INVITE.MAYBE:
                    sub_type = NOTIFY.NT_EVENT_REQ_MAYBE
                invite_id_list = []
                invite_id_list.append(data.row_id)
                add_event_creator_notification.s(
                    True, model.event_id, invite_id_list, sub_type).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (event_id, user_id)=(2, 2) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (event_id)=(9) is not present in table "event".
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
        return {'message': 'Updated Event Invite id: %s' %
                str(row_id)}, 200

    @swag_from('swagger_docs/event_invite_delete.yml')
    def delete(self, row_id):
        """
        Delete an event
        """
        model = None
        try:
            # first find model
            status = None
            event_id = None
            model = EventInvite.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Event Invite id: %s'
                        ' does not exist' % str(row_id))
            if model.created_by != g.current_user['row_id']:
                abort(403)
            status = model.status
            event_id = model.event_id
            db.session.delete(model)
            db.session.commit()
            data = Event.query.filter(Event.row_id == event_id).first()
            # if model is found, and not yet deleted, delete it
            if status == EVENT_INVITE.ACCEPTED:
                data.participated -= 1
                data.avg_rating = calculate_avg_rating(event_id)
                if data.participated < 0:
                    data.participated = 0
            elif status == EVENT_INVITE.REJECTED:
                data.not_participated -= 1
                if data.not_participated < 0:
                    data.not_participated = 0
            elif status == EVENT_INVITE.ATTENDED:
                data.attended_participated -= 1
                if data.attended_participated < 0:
                    data.attended_participated = 0
            elif status == EVENT_INVITE.MAYBE:
                data.maybe_participated -= 1
                if data.maybe_participated < 0:
                    data.maybe_participated = 0
            db.session.add(data)
            db.session.commit()
            # for update event counts and avg_rating
            manage_events_counts_and_avg_rating.s(
                True, event_id).delay()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204


class EventInvitesListAPI(AuthResource):
    """
    Read API for event lists, i.e, more than 1 event
    """
    model_class = EventInvite

    def __init__(self, *args, **kwargs):
        super(EventInvitesListAPI, self).__init__(*args, **kwargs)

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
        # user filter
        query_filters['base'].append(
            EventInvite.user_id == g.current_user['row_id'])
        query = self._build_final_query(query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/event_invite_get_list.yml')
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
                c_abort(404, message='No matching Event Invites found')
            result = event_invite_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
