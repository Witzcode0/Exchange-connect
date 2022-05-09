"""
API endpoints for "ca open meeting participants" package.
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
from app.corporate_access_resources.ca_open_meetings.models import \
    CAOpenMeeting
from app.corporate_access_resources.ca_open_meeting_participants.\
    models import CAOpenMeetingParticipant
from app.corporate_access_resources.ca_open_meeting_participants.\
    schemas import (CAOpenMeetingParticipantSchema,
                    CAOpenMeetingParticipantReadArgsSchema)


class CAOpenMeetingParticipantAPI(AuthResource):
    """
    CRUD API for managing ca open meeting participant
    """
    @swag_from('swagger_docs/ca_open_meeting_participants_post.yml')
    def post(self):
        """
        Create a ca open meeting participant
        """
        ca_open_participant_schema = CAOpenMeetingParticipantSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = ca_open_participant_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # for cancelled open meeting
            event = CAOpenMeeting.query.get(data.ca_open_meeting_id)
            if event.cancelled:
                c_abort(422, message='CA Open Meeting cancelled,'
                        ' so you cannot add a participant')
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (ca_open_meeting_id, participant_id)=(1, 1)
                # already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (participant_id)=(2) is not present in table "user".
                # Key (ca_open_meeting_id)=(4) is not present
                # in table "ca_open_meeting".
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

        return {'message': 'CA Open Meeting Participant added: %s' %
                           str(data.row_id), 'row_id': data.row_id}, 201

    @swag_from('swagger_docs/ca_open_meeting_participants_put.yml')
    def put(self, row_id):
        """
        Update a ca open meeting participant
        """
        ca_open_participant_schema = CAOpenMeetingParticipantSchema()
        # first find model
        model = None
        try:
            model = CAOpenMeetingParticipant.query.get(row_id)
            if model is None:
                c_abort(404, message='CA Open Meeting Participant id:'
                                     '%s does not exist' % str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
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
            data, errors = ca_open_participant_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # for cancelled open meeting
            event = CAOpenMeeting.query.get(model.ca_open_meeting_id)
            if event.cancelled:
                c_abort(422, message='CA Open Meeting cancelled,'
                        ' so you cannot update a participant')
            # no errors, so update data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (ca_open_meeting_id, participant_id)=(1, 1)
                # already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (participant_id)=(2) is not present in table "user".
                # Key (ca_open_meeting_id)=(4) is not present
                # in table "ca_open_meeting".
                column = e.orig.diag.message_detail.split('(')[1].split(')')[0]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
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
        return {'message': 'Updated CA Open Meeting Participant id: %s'
                           % str(row_id)}, 200

    @swag_from('swagger_docs/ca_open_meeting_participants_delete.yml')
    def delete(self, row_id):
        """
        Delete a ca open meeting participant
        """
        model = None
        try:
            # first find model
            model = CAOpenMeetingParticipant.query.get(row_id)
            if model is None:
                c_abort(404, message='CA Open Meeting Participant id:'
                                     ' %s does not exist' % str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            # for cancelled open meeting
            event = CAOpenMeeting.query.get(model.ca_open_meeting_id)
            if event.cancelled:
                c_abort(422, message='CA Open Meeting cancelled,'
                        ' so you cannot delete a participant')
            db.session.delete(model)
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

    @swag_from('swagger_docs/ca_open_meeting_participants_get.yml')
    def get(self, row_id):
        """
        Get a ca open meeting participant by id
        """
        ca_open_participant_schema = CAOpenMeetingParticipantSchema()
        model = None
        try:
            # first find model
            model = CAOpenMeetingParticipant.query.get(row_id)
            if model is None:
                c_abort(404, message='CA Open Meeting Participant id:'
                                     ' %s does not exist' % str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            result = ca_open_participant_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class CAOpenMeetingParticipantListAPI(AuthResource):
    """
    Read API for ca open meeting participant list, i.e, more than 1 participant
    """
    model_class = CAOpenMeetingParticipant

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['creator', 'participant',
                                    'ca_open_meeting']
        super(CAOpenMeetingParticipantListAPI, self).__init__(*args, **kwargs)

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

    @swag_from('swagger_docs/ca_open_meeting_participants_get_list.yml')
    def get(self):
        """
        Get the list
        """
        ca_open_participant_read_schema = \
            CAOpenMeetingParticipantReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            ca_open_participant_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(
                    filters, pfields, sort, pagination, db.session.query(
                        CAOpenMeetingParticipant), operator)
            # making a copy of the main output schema
            ca_open_participant_schema = CAOpenMeetingParticipantSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                ca_open_participant_schema = \
                    CAOpenMeetingParticipantSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching ca open meeting '
                        'participants found')
            result = ca_open_participant_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
