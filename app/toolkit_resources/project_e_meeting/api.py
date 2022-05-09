"""
API endpoints for "e_meeting" package.
"""
from werkzeug.exceptions import Forbidden, HTTPException
from flask_restful import abort
from sqlalchemy.orm import load_only
from sqlalchemy.orm import load_only, joinedload, contains_eager
from sqlalchemy import and_, any_, or_
from sqlalchemy.inspection import inspect
from flask import request, current_app, g
from sqlalchemy.exc import IntegrityError

from app import db, c_abort
from app.base.api import AuthResource
from app.base import constants as APP
from app.common.helpers import (
    store_file, delete_files, add_update_conference, delete_conference)
from app.resources.notifications import constants as NOTIFY
from app.toolkit_resources.project_e_meeting import constants as MEETING
from app.toolkit_resources.project_e_meeting.models import Emeeting
from app.toolkit_resources.project_e_meeting_invitee.models import (
    EmeetingInvitee)
from app.toolkit_resources.project_e_meeting.schemas import (
    EMeetingSchema, EmeetingReadArgsSchema)
from app.toolkit_resources.project_e_meeting_invitee.schemas import (
    EmeetingInviteeSchema)
from app.toolkit_resources.project_e_meeting.helpers import (
    pre_registration_user_for_conference)
from queueapp.e_meeting.emai_tasks import (
    send_emeeting_launch_email, send_emeeting_cancellation_email,
    send_emeeting_update_email)
from queueapp.e_meeting.notification_tasks import (
    add_emeeting_invite_notification,
    add_emeeting_updated_invitee_notification,
    add_emeeting_cancelled_invitee_notification)


class EmeetingAPI(AuthResource):
    """
    CRUD API for managing Emeeting
    """

    def post(self):
        """
        Create a Emeeting
        """
        e_meeting_schema = EMeetingSchema()
        json_data = request.get_json()
        emeeting_invitees = []

        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = e_meeting_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.account_id = g.current_user['account_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()

            # manage invitees
            if e_meeting_schema._cached_project_users:
                for invitee in e_meeting_schema._cached_project_users:

                    if invitee not in data.invitees:
                        emeeting_invitees.append(invitee)
                        db.session.add(EmeetingInvitee(
                            e_meeting_id=data.row_id,
                            invitee_id=invitee,
                            created_by=data.created_by,
                            updated_by=data.created_by))
                db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                column = e.orig.diag.message_detail.split('(')[1].split(')')[0]
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

        # Big-marker url generate
        try:
            response = add_update_conference(data)
            if not response['status']:
                db.session.delete(data)
                db.session.commit()
                c_abort(422, message='problem with bigmarker',
                        errors=response['response'].get('error', {}))
            if response['conference_id']:
                pre_registration_user_for_conference(emeeting=data)
                send_emeeting_launch_email.s(True, data.row_id).delay()
                if data.e_meeting_invitees:
                    add_emeeting_invite_notification.s(
                        True, emeeting_invitees, data.row_id,
                        NOTIFY.NT_EMEETING_INVITED
                    ).delay()

                # true specifies mail sending task is in queue
                data.is_in_process = True
                db.session.add(data)
                db.session.commit()
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            db.session.delete(data)
            db.session.commit()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'E_meeting created: %s' %
                           str(data.row_id), 'row_id': data.row_id}, 201

    def put(self, row_id):
        """
        Update a Emeeting
        """
        e_meeting_schema = EMeetingSchema(strict=True)
        # first find model
        model = None
        emeeting_invitees = []
        try:
            model = Emeeting.query.get(row_id)
            if model is None:
                c_abort(404, message='Emeeting id:'
                        '%s does not exist' % str(row_id))

            if model.created_by != g.current_user['row_id']:
                abort(403)

        except HTTPException as e:
            raise e
        except Exception as e:
            abort(500)

        try:
            # get the json data from the request
            json_data = request.get_json()
            old_meeting_datetime = model.meeting_datetime

            if (not json_data):  # no rsvp
                # no data of any sort
                c_abort(400)
            # validate and deserialize input
            data = None
            if json_data:
                data, errors = e_meeting_schema.load(
                    json_data, instance=model, partial=True)
                if errors:
                    c_abort(422, errors=errors)
            if not data:
                data = model

            # no errors, so update data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()

            rescheduled = old_meeting_datetime != data.meeting_datetime
            # manage invitees
            final_invitee_email_ids = []
            invitee_email_ids = []
            if (e_meeting_schema._cached_project_users or
                    'invitee_ids' in json_data):

                for invitee in e_meeting_schema._cached_project_users:

                    if invitee not in list(map(
                            lambda a: a.row_id, data.invitees)):
                        emeeting_invitees.append(invitee)
                        db.session.add(EmeetingInvitee(
                            e_meeting_id=data.row_id,
                            invitee_id=invitee,
                            created_by=g.current_user['row_id'],
                            updated_by=g.current_user['row_id']))

                db.session.commit()

        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                column = e.orig.diag.message_detail.split('(')[1].split(')')[0]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # already exists.
                column = e.orig.diag.message_detail.split('(')[1].split(')')[0]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except HTTPException as e:
            raise e
        except Forbidden as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        try:
            if rescheduled:
                response = add_update_conference(data)
                if not response['status']:
                    c_abort(422, message='problem with bigmarker',
                            errors=response['response'].get('error', {}))
                send_emeeting_update_email.s(
                    True, row_id, rescheduled).delay()
                if data.e_meeting_invitees:
                    add_emeeting_updated_invitee_notification.s(
                        True, data.row_id, NOTIFY.NT_EMEETING_RESCHUDLE
                    ).delay()

            if emeeting_invitees:
                pre_registration_user_for_conference(emeeting=data)
                add_emeeting_invite_notification.s(
                    True, emeeting_invitees, data.row_id, NOTIFY.NT_EMEETING_INVITED
                ).delay()
                send_emeeting_launch_email.s(True, data.row_id).delay()

        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            db.session.commit()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Updated Emeeting id: %s' % str(row_id)}, 200

    def delete(self, row_id):
        """
        Delete a Emeeting
        """
        model = None
        try:
            # first find model
            model = Emeeting.query.get(row_id)
            if model is None:
                c_abort(404, message='Emeeting id: %s does not exist' %
                                     str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            if model.cancelled:
                c_abort(422, message='Emeeting cancelled,'
                        ' so it cannot be deleted')

            # delete bigmarker id
            conference_id = model.conference_id

            if conference_id:
                response = delete_conference(conference_id=conference_id)
                if not response['status']:
                    c_abort(422, message='problem with bigmarker',
                            errors=response['response'])

            db.session.delete(model)
            db.session.commit()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            abort(500)
        return {}, 204

    def get(self, row_id):
        """
        Get a Emeeting by id
        """
        model = None
        try:
            # first find model
            model = Emeeting.query.filter(Emeeting.row_id == row_id).join(
                EmeetingInvitee, and_(
                    EmeetingInvitee.e_meeting_id == Emeeting.row_id,
                    EmeetingInvitee.invitee_id == g.current_user['row_id']),
                isouter=True).options(contains_eager(Emeeting.invited)).first()
            if model is None:
                c_abort(404, message='Emeeting id:'
                        ' %s does not exist' % str(row_id))
            # check ownership
            # for invitee users
            invitee_user_ids = []
            for meeting in EmeetingInvitee.query.filter(
                    EmeetingInvitee.e_meeting_id == row_id):
                if meeting.invitee_id:
                    invitee_user_ids.append(meeting.invitee_id)
            invitee_user_ids.append(model.created_by)
            if (g.current_user['row_id'] not in invitee_user_ids):
                abort(403)

            local_exclude_list = EMeetingSchema._default_exclude_fields[:]

            result = EMeetingSchema(exclude=local_exclude_list).dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class EmeetingCancelAPI(AuthResource):
    """
    cancel API for manage cancelled meeting
    """

    def put(self, row_id):
        """
        Update a Emeeting
        """
        e_meeting_schema = EMeetingSchema()
        # first find model
        model = None
        try:
            model = Emeeting.query.get(row_id)
            if model is None:
                c_abort(404, message='Emeeting id:'
                        '%s does not exist' % str(row_id))

            if model.created_by != g.current_user['row_id']:
                abort(403)

        except HTTPException as e:
            raise e
        except Exception as e:
            abort(500)

        try:
            # get the json data from the request
            model.cancelled = True
            data = model
            data.updated_by = g.current_user['row_id']

            # delete bigmarker id
            conference_id = data.conference_id

            if conference_id:
                response = delete_conference(conference_id=conference_id)
                if not response['status']:
                    c_abort(422, message='problem with bigmarker',
                            errors=response['response'])

            db.session.add(data)
            db.session.commit()
            send_emeeting_cancellation_email.s(True, row_id).delay()
            # send emeeting cancel notification to invitee
            add_emeeting_cancelled_invitee_notification.s(
                True, row_id, NOTIFY.NT_EMEETING_CANCELLED).delay()

        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                column = e.orig.diag.message_detail.split('(')[1].split(')')[0]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # already exists.
                column = e.orig.diag.message_detail.split('(')[1].split(')')[0]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except HTTPException as e:
            raise e
        except Forbidden as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Emeeting id: %s cancelled' % str(row_id)}, 200


class EmeetingListAPI(AuthResource):
    """
    Read API for Emeeting lists, i.e, more than 1
    """
    model_class = Emeeting

    def __init__(self, *args, **kwargs):
        super(EmeetingListAPI, self).__init__(*args, **kwargs)

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
        main_filter = None
        innerjoin = False

        if extra_query:
            mapper = inspect(self.model_class)
            for f in extra_query:
                # dates

                if (f in ['meeting_datetime_from', 'meeting_datetime_to']
                        and extra_query[f]):

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
                elif f == 'main_filter':
                    main_filter = extra_query[f]

        # for union query without current_user filter
        query_filters_union = {}
        query_filters_union['base'] = query_filters['base'][:]
        query_filters_union['filters'] = query_filters['filters'][:]

        query_for_union = self._build_final_query(
            query_filters_union, query_session, operator)

        query_filters['base'].append(
            Emeeting.created_by == g.current_user['row_id'])

        query = self._build_final_query(
            query_filters, query_session, operator)

        join_load = [
            contains_eager(Emeeting.invited),
            # invitees and related stuff
            joinedload(Emeeting.invitees, innerjoin=innerjoin)]

        query_for_union = query_for_union.join(
            EmeetingInvitee,
            and_(EmeetingInvitee.e_meeting_id == Emeeting.row_id,
                 EmeetingInvitee.invitee_id == g.current_user['row_id'],
                 )).options(*join_load)

        # eager load
        query = query.options(*join_load)

        if not main_filter or main_filter == MEETING.MNFT_ALL:
            # for showing Emeeting current user created,
            # invited, hosted or participated
            final_query = query.union(query_for_union)

            final_query = final_query.join(EmeetingInvitee, and_(
                EmeetingInvitee.e_meeting_id == Emeeting.row_id,
                EmeetingInvitee.invitee_id == g.current_user['row_id']),
                isouter=True)

        elif main_filter == MEETING.MNFT_INVITED:
            # for showing Emeeting current user is invited to

            final_query = query_for_union

        elif main_filter == MEETING.MNFT_MINE:
            # for showing only Emeeting created by current user
            # join for Emeeting invited
            final_query = query.join(EmeetingInvitee, and_(
                EmeetingInvitee.e_meeting_id == Emeeting.row_id,
                EmeetingInvitee.invitee_id == g.current_user['row_id']),
                isouter=True)

        return final_query, db_projection, s_projection, order, paging

    def get(self):
        """
        Get the list
        """
        e_meeting_read_schema = EmeetingReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            e_meeting_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Emeeting), operator)
            # making a copy of the main output schema
            e_meeting_schema = EMeetingSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                e_meeting_schema = EMeetingSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching meeting found')
            result = e_meeting_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            abort(500)
        return {'results': result.data, 'total': total}, 200
