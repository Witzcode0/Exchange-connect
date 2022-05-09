"""
API endpoints for "webinar participants" package.
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
from app.webinar_resources.webinar_participants.models import (
    WebinarParticipant)
from app.webinar_resources.webinar_participants.schemas import (
    WebinarParticipantSchema, WebinarParticipantReadArgsSchema)
from app.webinar_resources.webinars.models import Webinar

from queueapp.webinars.stats_tasks import update_webinar_stats


class WebinarParticipantAPI(AuthResource):
    """
    CRUD API for managing Webinar participant
    """
    @swag_from('swagger_docs/webinar_participants_post.yml')
    def post(self):
        """
        Create a Webinar Participant
        """
        webinar_participant_schema = WebinarParticipantSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = webinar_participant_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # for cancelled webinar
            webinar = Webinar.query.get(data.webinar_id)
            if webinar.cancelled:
                c_abort(422, errors='Webinar cancelled,'
                        ' so you cannot add participants')
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()
            # update webinar stats
            update_webinar_stats.s(True, data.webinar_id).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (webinar_id, participant_id)=(3,3) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (webinar_id)=(5) is not present in table "webinar".
                # Key (participant_id)=(5) is not present in table "user".
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

        return {'message': 'Webinar Participant added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @swag_from('swagger_docs/webinar_participants_put.yml')
    def put(self, row_id):
        """
        Update a Webinar Participant
        """
        webinar_participant_schema = WebinarParticipantSchema()
        # first find model
        model = None
        try:
            model = WebinarParticipant.query.get(row_id)
            if model is None:
                c_abort(404, message='Webinar Participant id:'
                                     '%s does not exist' % str(row_id))
            # old_webinar_id, to be used for stats calculation
            wb_id = model.webinar_id
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
            data, errors = webinar_participant_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # for cancelled webinar
            webinar = Webinar.query.get(model.webinar_id)
            if webinar.cancelled:
                c_abort(422, message='Webinar cancelled,'
                        'so you cannot update participants')
            # no errors, so update data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()
            if wb_id != model.webinar_id:
                # update webinar stats
                update_webinar_stats.s(True, model.webinar_id).delay()
                update_webinar_stats.s(True, wb_id).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (webinar_id, participant_id)=(3,3) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                current_app.logger.exception(e)
                # format of the message:
                # Key (webinar_id)=(5) is not present in table "webinar".
                # Key (participant_id)=(5) is not present in table "user".
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
        return {'message': 'Updated Webinar Participant id: %s' %
                           str(row_id)}, 200

    @swag_from('swagger_docs/webinar_participants_delete.yml')
    def delete(self, row_id):
        """
        Delete a Webinar Participant
        """
        model = None
        try:
            # first find model
            model = WebinarParticipant.query.get(row_id)
            if model is None:
                c_abort(404, message='Webinar Participant id: %s'
                                     ' does not exist' % str(row_id))
            # old_webinar_id, to be used for stats calculation
            wb_id = model.webinar_id
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            # for cancelled webinar
            webinar = Webinar.query.get(wb_id)
            if webinar.cancelled:
                c_abort(422, message='Webinar cancelled,'
                        'so you cannot delete participants')
            db.session.delete(model)
            db.session.commit()
            # update webinar stats
            update_webinar_stats.s(True, wb_id).delay()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204

    @swag_from('swagger_docs/webinar_participants_get.yml')
    def get(self, row_id):
        """
        Get a Webinar Participant by id
        """
        model = None
        try:
            # first find model
            model = WebinarParticipant.query.get(row_id)
            if model is None:
                c_abort(404, message='Webinar Participant id:'
                                     ' %s does not exist' % str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            result = WebinarParticipantSchema(
                exclude=WebinarParticipantSchema._default_exclude_fields
            ).dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class WebinarParticipantListAPI(AuthResource):
    """
    Read API for Webinar Participant lists, i.e, more than 1
    """
    model_class = WebinarParticipant

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['creator', 'participant', 'webinar']
        super(WebinarParticipantListAPI, self).__init__(*args, **kwargs)

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

    @swag_from('swagger_docs/webinar_participants_get_list.yml')
    def get(self):
        """
        Get the list
        """
        webinar_participant_read_schema = WebinarParticipantReadArgsSchema(
            strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            webinar_participant_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(WebinarParticipant),
                                 operator)
            # making a copy of the main output schema
            webinar_participant_schema = WebinarParticipantSchema(
                exclude=WebinarParticipantSchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                webinar_participant_schema = WebinarParticipantSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching webinar participants found')
            result = webinar_participant_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
