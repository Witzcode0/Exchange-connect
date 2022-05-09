"""
API endpoints for "webinar_chats" package.
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
from app.webinar_resources.webinars.models import Webinar
from app.webinar_resources.webinar_chats.models import WebinarChatMessage
from app.webinar_resources.webinar_chats.schemas import (
    WebinarChatMessageSchema, WebinarChatMessageReadArgsSchema)

from queueapp.webinars.stats_tasks import update_webinar_stats


class WebinarChatMessageAPI(AuthResource):
    """
    CRUD API for managing webinar_chats
    """
    @swag_from('swagger_docs/webinar_chats_post.yml')
    def post(self):
        """
        Create a webinar_chats
        """
        webinar_chat_message_schema = WebinarChatMessageSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = webinar_chat_message_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # for cancelled webinar
            webinar = Webinar.query.get(data.webinar_id)
            if webinar.cancelled:
                c_abort(422, errors='Webinar cancelled,'
                        ' so you cannot add a chat message')
            # no errors, so add data to db
            data.sent_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()
            # update webinar stats
            update_webinar_stats.s(True, data.webinar_id).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (sent_to)=(2) is not present in table "user"
                # Key (webinar_id)=(22) is not present in table "webinar".
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

        return {'message': 'Webinar Chat Message added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @swag_from('swagger_docs/webinar_chats_put.yml')
    def put(self, row_id):
        """
        Update a webinar_chats
        """
        webinar_chat_message_schema = WebinarChatMessageSchema()
        # first find model
        model = None
        try:
            model = WebinarChatMessage.query.get(row_id)
            if model is None:
                c_abort(404,
                        message='Webinar Chat Message id: %s does not exist' %
                        str(row_id))
            # old_webinar_id, to be used for stats calculation
            wb_id = model.webinar_id
            # check ownership
            if model.sent_by != g.current_user['row_id']:
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
            data, errors = webinar_chat_message_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # for cancelled webinar
            webinar = Webinar.query.get(model.webinar_id)
            if webinar.cancelled:
                c_abort(422, message='Webinar cancelled,'
                        ' so you cannot update a chat message')
            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
            if wb_id != model.webinar_id:
                # update webinar stats
                update_webinar_stats.s(True, model.webinar_id).delay()
                update_webinar_stats.s(True, wb_id).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (sent_to)=(2) is not present in table "user"
                # Key (webinar_id)=(22) is not present in table "webinar".
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
        return {'message': 'Updated Webinar Chat Message id: %s' %
                str(row_id)}, 200

    @swag_from('swagger_docs/webinar_chats_delete.yml')
    def delete(self, row_id):
        """
        Delete a webinar_chats
        """
        model = None
        try:
            # first find model
            model = WebinarChatMessage.query.get(row_id)
            if model is None:
                c_abort(404,
                        message='Webinar Chat Message id: %s does not exist' %
                        str(row_id))
            # for cancelled webinar
            webinar = Webinar.query.get(model.webinar_id)
            if webinar.cancelled:
                c_abort(422, message='Webinar cancelled,'
                        ' so you cannot delete a chat message')
            # old_webinar_id, to be used for stats calculation
            wb_id = model.webinar_id
            # check ownership
            if model.sent_by != g.current_user['row_id']:
                abort(403)
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

    @swag_from('swagger_docs/webinar_chats_get.yml')
    def get(self, row_id):
        """
        Get a webinar_chats by id
        """
        webinar_chat_message_schema = WebinarChatMessageSchema()
        model = None
        try:
            # first find model
            model = WebinarChatMessage.query.get(row_id)
            if model is None:
                c_abort(404,
                        message='Webinar Chat Message id: %s does not exist' %
                        str(row_id))
            result = webinar_chat_message_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class WebinarChatMessageListAPI(AuthResource):
    """
    Read API for webinar_chats lists, i.e, more than 1 webinar_chats
    """
    model_class = WebinarChatMessage

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['sender', 'webinar']
        super(WebinarChatMessageListAPI, self).__init__(*args, **kwargs)

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

    @swag_from('swagger_docs/webinar_chats_get_list.yml')
    def get(self):
        """
        Get the list
        """
        webinar_chat_message_read_schema = WebinarChatMessageReadArgsSchema(
            strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            webinar_chat_message_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(WebinarChatMessage),
                                 operator)
            # making a copy of the main output schema
            webinar_chat_message_schema = WebinarChatMessageSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                webinar_chat_message_schema = WebinarChatMessageSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching webinar chats found')
            result = webinar_chat_message_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
