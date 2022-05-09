"""
API endpoints for "project_chats" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from flasgger.utils import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.toolkit_resources.project_chats.models import ProjectChatMessage
from app.toolkit_resources.project_chats.schemas import (
    ProjectChatMessageSchema, ProjectChatMessageReadArgsSchema)
from app.base import constants as APP


class ProjectChatMessageAPI(AuthResource):
    """
    CRUD API for managing project_chats
    """

    @swag_from('swagger_docs/project_chats_post.yml')
    def post(self):
        """
        Create a project_chats
        """

        project_chat_message_schema = ProjectChatMessageSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = project_chat_message_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.sent_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (project_id)=(220) is not present in table "project".
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

        return {'message': 'Project Chat Message added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @swag_from('swagger_docs/project_chats_put.yml')
    def put(self, row_id):
        """
        Update a project_chats
        """

        project_chat_message_schema = ProjectChatMessageSchema()
        # first find model
        model = None
        try:
            model = ProjectChatMessage.query.get(row_id)
            if model is None:
                c_abort(404,
                        message='Project Chat Message id: %s does not exist' %
                        str(row_id))
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
            data, errors = project_chat_message_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (project_id)=(220) is not present in table "project".
                column = e.orig.diag.message_detail.split('(')[1].split(')')[0]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except Forbidden as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Updated Project Chat Message id: %s' %
                str(row_id)}, 200

    @swag_from('swagger_docs/project_chats_delete.yml')
    def delete(self, row_id):
        """
        Delete a project_chats
        """

        model = None
        try:
            # first find model
            model = ProjectChatMessage.query.get(row_id)
            if model is None:
                c_abort(404,
                        message='Project Chat Message id: %s does not exist' %
                        str(row_id))
            # check ownership
            if model.sent_by != g.current_user['row_id']:
                abort(403)
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

    @swag_from('swagger_docs/project_chats_get.yml')
    def get(self, row_id):
        """
        Get a project_chats by id
        """

        project_chat_message_schema = ProjectChatMessageSchema()
        model = None
        try:
            # first find model
            model = ProjectChatMessage.query.get(row_id)
            if model is None:
                c_abort(404,
                        message='Project Chat Message id: %s does not exist' %
                        str(row_id))
            result = project_chat_message_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class ProjectChatMessageListAPI(AuthResource):
    """
    Read API for project_chats lists, i.e, more than 1 project_chats
    """

    model_class = ProjectChatMessage

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['sender', 'project']
        super(ProjectChatMessageListAPI, self).__init__(*args, **kwargs)

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

    @swag_from('swagger_docs/project_chats_get_list.yml')
    def get(self):
        """
        Get the list
        """
        project_chat_message_read_schema = ProjectChatMessageReadArgsSchema(
            strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            project_chat_message_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(ProjectChatMessage),
                                 operator)
            # making a copy of the main output schema
            project_chat_message_schema = ProjectChatMessageSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                project_chat_message_schema = ProjectChatMessageSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching project_chats found')
            result = project_chat_message_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
