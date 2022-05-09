"""
API endpoints for "events" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only, joinedload, contains_eager, Load
from sqlalchemy import and_, or_
from sqlalchemy.inspection import inspect
from flasgger.utils import swag_from

from app import db, c_abort
from app.base import constants as APP
from app.base.api import AuthResource
from app.base.schemas import account_fields
from app.resources.events.models import Event
from app.resources.accounts.models import Account
from app.resources.event_invites.models import EventInvite
from app.resources.event_bookmarks.models import EventBookmark
from app.resources.event_file_library.models import EventLibraryFile
from app.resources.events.schemas import (
    EventSchema, EventReadArgsSchema)
from app.resources.users.models import User
from app.resources.events import constants as EVENT
from app.resources.notifications import constants as NOTIFY

from queueapp.notification_tasks import add_event_invite_notifications
from queueapp.event_tasks import manage_events_counts_and_avg_rating


# main input and output schema
event_schema = EventSchema()
# schema for reading get arguments
event_read_schema = EventReadArgsSchema(strict=True)


class EventAPI(AuthResource):
    """
    For creating new events
    """
    @swag_from('swagger_docs/event_post.yml')
    def post(self):
        """
        Create an event
        """
        # invitee_ids = None
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = event_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.account_id = g.current_user['account_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()
            # manage files
            if event_schema._cached_files or 'file_ids' in json_data:
                for cf in event_schema._cached_files:
                    if cf not in data.files:
                        data.files.append(cf)
                db.session.commit()

            # manage invites
            if event_schema._cached_contact_users:
                invitee_ids = []
                for ccu in event_schema._cached_contact_users:
                    if ccu not in data.invitees:
                        db.session.add(EventInvite(
                            event_id=data.row_id, user_id=ccu.row_id,
                            created_by=data.created_by,
                            updated_by=data.created_by))
                        invitee_ids.append(ccu.row_id)
                db.session.commit()
                # notify invitees
                add_event_invite_notifications.s(
                    True, data.row_id, invitee_ids,
                    NOTIFY.NT_EVENT_REQ_REQUESTED).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (event_type_id)=(4) is not present in table "event_type".
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

        return {'message': 'Event created: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201

    @swag_from('swagger_docs/event_get.yml')
    def get(self, row_id):
        """
        Get a event by id
        """
        model = None
        try:
            # first find model
            model = Event.query.options(
                joinedload(Event.invites),
                joinedload(Event.event_type)).get(row_id)

            if model is None or model.deleted:
                c_abort(404, message='Event id: %s'
                        ' does not exist' % str(row_id))
            result = event_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200

    @swag_from('swagger_docs/event_put.yml')
    def put(self, row_id):
        """
        Update an event
        """
        # first find model
        model = None
        try:
            model = Event.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Event id: %s'
                        ' does not exist' % str(row_id))
            if model.created_by != g.current_user['row_id']:
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
            data, errors = event_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            data.account_id = g.current_user['account_id']
            db.session.add(data)
            db.session.commit()
            # manage event files
            if event_schema._cached_files or 'file_ids' in json_data:
                # add new ones
                for cf in event_schema._cached_files:
                    if cf not in data.files:
                        data.files.append(cf)
                # remove old ones
                for oldcf in data.files[:]:
                    if oldcf not in event_schema._cached_files:
                        data.files.remove(oldcf)
                db.session.commit()
            # manage event invites list
            if (event_schema._cached_contact_users or
                    'invitee_ids' in json_data):
                # #TODO: eager load invitees for faster checks
                # add new ones by checking users
                invitee_ids = []
                for ccu in event_schema._cached_contact_users:
                    if ccu not in data.invitees:
                        invitee_ids.append(ccu.row_id)
                        db.session.add(EventInvite(
                            event_id=data.row_id, user_id=ccu.row_id,
                            created_by=g.current_user['row_id'],
                            updated_by=g.current_user['row_id']))
                # remove old ones
                for oldinvite in data.invites[:]:
                    if (oldinvite.invitee not in
                            event_schema._cached_contact_users):
                        if oldinvite in data.invites:
                            db.session.delete(oldinvite)
                            db.session.commit()
                db.session.commit()
                # for update event counts and avg_rating
                manage_events_counts_and_avg_rating.s(
                    True, data.row_id).delay()
                # notify new invitees
                add_event_invite_notifications.s(
                    True, data.row_id, invitee_ids,
                    NOTIFY.NT_EVENT_REQ_REQUESTED).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (event_type_id)=(4) is not present in table "event_type".
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
        return {'message': 'Updated Event id: %s' % str(row_id)}, 200

    @swag_from('swagger_docs/event_delete.yml')
    def delete(self, row_id):
        """
        Delete an event
        """
        model = None
        try:
            # first find model
            model = Event.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Event id: %s'
                        ' does not exist' % str(row_id))
            if model.created_by != g.current_user['row_id']:
                abort(403)
            # if model is found, and not yet deleted, delete it
            model.updated_by = g.current_user['row_id']
            model.deleted = True
            db.session.add(model)
            # deleting invites from event invites
            EventInvite.query.filter(EventInvite.event_id == row_id).delete()
            # deleting bookmarks from event bookmarks
            EventBookmark.query.filter(
                EventBookmark.event_id == row_id).delete()
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


class EventsListAPI(AuthResource):
    """
    Read API for event lists, i.e, more than 1 event
    """
    model_class = Event

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = [
            'invitee_ids', 'participated', 'not_participated',
            'maybe_participated', 'rating', 'invites', 'invitees',
            'participants', 'non_participants', 'maybe_participants',
            'attended_participated', 'attended_participants']
        super(EventsListAPI, self).__init__(*args, **kwargs)

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
        if extra_query:
            mapper = inspect(self.model_class)
            for f in extra_query:
                # dates
                if f in ['start_date_from', 'start_date_to',
                         'end_date_from', 'end_date_to'] and extra_query[f]:
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
                # invitees
                elif f == 'invitee_ids':
                    query_filters['filters'].append(
                        EventInvite.user_id.in_(filters[f]))
                    innerjoin = True
                    continue
                elif f == 'file_ids':
                    query_filters['filters'].append(
                        EventLibraryFile.row_id.in_(filters[f]))
                    innerjoin = True
                    continue
                elif f == 'main_filter':
                    main_filter = extra_query[f]

        # for union query without current_user filter
        query_for_union = self._build_final_query(
            query_filters, query_session, operator)

        # for normal query
        query_filters['base'].append(or_(
            Event.open_to_all, Event.public_event,
            Event.created_by == g.current_user['row_id']))
        query = self._build_final_query(query_filters, query_session, operator)

        join_load = [
            # let it know that this is already loaded
            contains_eager(Event.event_bookmarked),
            # files
            joinedload(Event.files, innerjoin=innerjoin),
            # invites and related stuff
            joinedload(Event.invites, innerjoin=innerjoin),
            # invitees and related stuff
            joinedload(Event.invitees, innerjoin=innerjoin).load_only(
                'row_id', 'account_id').joinedload(
                User.account).load_only(*account_fields),
            joinedload(Event.invitees, innerjoin=innerjoin).load_only(
                'row_id').joinedload(User.profile),
            # participants and related stuff
            joinedload(Event.participants).load_only(
                'row_id', 'account_id').joinedload(
                User.account).load_only(*account_fields),
            joinedload(Event.participants).load_only('row_id').joinedload(
                User.profile),
            # non_participants and related stuff
            joinedload(Event.non_participants).load_only(
                'row_id', 'account_id').joinedload(
                User.account).load_only(*account_fields),
            joinedload(Event.non_participants).load_only(
                'row_id').joinedload(User.profile),
            # maybe_participants and related stuff
            joinedload(Event.maybe_participants).load_only(
                'row_id', 'account_id').joinedload(
                User.account).load_only(*account_fields),
            joinedload(Event.maybe_participants).load_only(
                'row_id').joinedload(User.profile),
            # maybe_participants and related stuff
            joinedload(Event.attended_participants).load_only(
                'row_id', 'account_id').joinedload(
                User.account).load_only(*account_fields),
            joinedload(Event.attended_participants).load_only(
                'row_id').joinedload(User.profile),
            # event type related stuff
            joinedload(Event.event_type),
            # creator and related stuff
            joinedload(Event.creator).load_only(
                'row_id').joinedload(User.profile),
            joinedload(Event.creator).load_only(
                'row_id', 'account_id').joinedload(
                User.account).joinedload(Account.profile)]

        # eager load
        query = query.options(*join_load)

        if not main_filter or main_filter == EVENT.MNFT_ALL:
            # for showing events current user either created or invited to
            query_union = query_for_union.join(EventInvite, and_(
                EventInvite.event_id == Event.row_id,
                EventInvite.user_id == g.current_user['row_id'])).options(
                *join_load)
            final_query = query.union(query_union)
        elif main_filter == EVENT.MNFT_MINE:
            # for showing only events created by current user
            # for normal query
            query_filters['base'].append(
                Event.created_by == g.current_user['row_id'])
            query = self._build_final_query(
                query_filters, query_session, operator)
            final_query = query.options(*join_load)
        elif main_filter == EVENT.MNFT_INVITED:
            # for showing events current user is invited to
            query_union = query_for_union.join(EventInvite, and_(
                EventInvite.event_id == Event.row_id,
                EventInvite.user_id == g.current_user['row_id'])).options(
                *join_load)
            final_query = query.union(query_union).\
                filter(Event.created_by != g.current_user['row_id'])
        elif main_filter == EVENT.MNFT_REQUESTED:
            # for showing events current user is requested to
            final_query = query_for_union.join(EventInvite, and_(
                EventInvite.event_id == Event.row_id,
                EventInvite.user_id == g.current_user['row_id'],
                EventInvite.status == EVENT.MNFT_REQUESTED)).options(
                *join_load)
        final_query = final_query.join(
            EventBookmark, and_(
                EventBookmark.event_id == Event.row_id,
                EventBookmark.created_by == g.current_user['row_id']),
            isouter=True)

        return final_query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/event_get_list.yml')
    def get(self):
        """
        Get the list
        """
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            event_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Event),
                                 operator)
            # making a copy of the main output schema
            event_schema = EventSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                event_schema = EventSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching Events found')
            result = event_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
