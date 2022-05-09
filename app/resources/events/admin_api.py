"""
API endpoints for "events" package for admin user.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only, joinedload
from sqlalchemy.inspection import inspect
from flasgger.utils import swag_from

from app import db, c_abort
from app.base import constants as APP
from app.auth.decorators import role_permission_required
from app.base.api import AuthResource
from app.base.schemas import account_fields
from app.resources.events.models import Event
from app.resources.accounts.models import Account
from app.resources.event_bookmarks.models import EventBookmark
from app.resources.event_invites.models import EventInvite
from app.resources.event_file_library.models import EventLibraryFile
from app.resources.events.schemas import (
    AdminEventSchema, AdminEventReadArgsSchema)
from app.resources.users.models import User
from app.resources.roles import constants as ROLE
from app.resources.roles.models import Role

from queueapp.notification_tasks import add_event_invite_notifications


# main input and output schema
admin_event_schema = AdminEventSchema()
# schema for reading get arguments
admin_event_read_schema = AdminEventReadArgsSchema(strict=True)


class AdminEventAPI(AuthResource):
    """
    For creating new events by admin
    """
    @role_permission_required(perms=[ROLE.EPT_NU])
    @swag_from('swagger_docs/admin_event_post.yml')
    def post(self):
        """
        Create an event by admin
        """
        # invitee_ids = None
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)
        try:
            # validate and deserialize input into object
            data, errors = admin_event_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()
            # manage files
            if admin_event_schema._cached_files or 'file_ids' in json_data:
                for cf in admin_event_schema._cached_files:
                    if cf not in data.files:
                        data.files.append(cf)
                db.session.commit()
            # manage invites
            if admin_event_schema._cached_contact_users:
                invitee_ids = []
                for ccu in admin_event_schema._cached_contact_users:
                    if ccu not in data.invitees:
                        db.session.add(EventInvite(
                            event_id=data.row_id, user_id=ccu.row_id,
                            created_by=data.created_by,
                            updated_by=data.created_by))
                        invitee_ids.append(ccu.row_id)
                db.session.commit()
                # notify invitees
                add_event_invite_notifications.s(
                    True, data.row_id, invitee_ids).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (name)=(example@example.com) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXIST, errors={
                    column: [APP.MSG_ALREADY_EXIST]})
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

    @role_permission_required(perms=[ROLE.EPT_NU])
    @swag_from('swagger_docs/admin_event_get.yml')
    def get(self, row_id):
        """
        Get a registration request by id
        """
        model = None
        try:
            # first find model
            model = Event.query.options(joinedload(Event.invites)).get(row_id)

            if model is None or model.deleted:
                c_abort(404, message='Event id: %s'
                        ' does not exist' % str(row_id))
            result = admin_event_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200

    @role_permission_required(perms=[ROLE.EPT_NU])
    @swag_from('swagger_docs/admin_event_put.yml')
    def put(self, row_id):
        """
        Update an event by admin user
        """
        # first find model
        model = None
        try:
            model = Event.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Event id: %s'
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
            # validate and deserialize input
            data, errors = admin_event_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()
            # manage event files
            if admin_event_schema._cached_files or 'file_ids' in json_data:
                # add new ones
                for cf in admin_event_schema._cached_files:
                    if cf not in data.files:
                        data.files.append(cf)
                # remove old ones
                for oldcf in data.files[:]:
                    if oldcf not in admin_event_schema._cached_files:
                        data.files.remove(oldcf)
                db.session.commit()
            # manage event invites list
            if (admin_event_schema._cached_contact_users or
                    'invitee_ids' in json_data):
                # #TODO: eager load invitees for faster checks
                # add new ones by checking users
                invitee_ids = []
                for ccu in admin_event_schema._cached_contact_users:
                    if ccu not in data.invitees:
                        invitee_ids.append(ccu.row_id)
                        db.session.add(EventInvite(
                            event_id=data.row_id, user_id=ccu.row_id,
                            created_by=data.created_by,
                            updated_by=data.updated_by))
                # remove old ones
                for oldinvite in data.invites[:]:
                    if (oldinvite.invitee not in
                            admin_event_schema._cached_contact_users):
                        if oldinvite in data.invites:
                            db.session.delete(oldinvite)
                db.session.commit()
                # notify new invitees
                add_event_invite_notifications.s(
                    True, data.row_id, invitee_ids).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (name)=(example@example.com) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXIST, errors={
                    column: [APP.MSG_ALREADY_EXIST]})
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

    @role_permission_required(perms=[ROLE.EPT_NU])
    @swag_from('swagger_docs/admin_event_delete.yml')
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


class AdminEventsListAPI(AuthResource):
    """
    Read API for event lists, i.e, more than 1 event
    """
    model_class = Event

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = [
            'invitee_ids', 'participated', 'not_participated',
            'maybe_participated' 'rating', 'invites', 'invitees',
            'participants', 'non_participants', 'maybe_participants']
        super(AdminEventsListAPI, self).__init__(*args, **kwargs)

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

        query = self._build_final_query(query_filters, query_session, operator)

        join_load = [
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
            # creator and related stuff
            joinedload(Event.creator).load_only(
                'row_id').joinedload(User.profile),
            joinedload(Event.creator).load_only(
                'row_id', 'account_id').joinedload(
                User.account).joinedload(Account.profile)]
        # eager loading
        query = query.options(*join_load)

        return query, db_projection, s_projection, order, paging

    @role_permission_required(perms=[ROLE.EPT_NU])
    @swag_from('swagger_docs/admin_event_get_list.yml')
    def get(self):
        """
        Get the list for admin
        """
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            admin_event_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Event),
                                 operator)
            # making a copy of the main output schema
            admin_event_schema = AdminEventSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                admin_event_schema = AdminEventSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching Events found')
            result = admin_event_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
