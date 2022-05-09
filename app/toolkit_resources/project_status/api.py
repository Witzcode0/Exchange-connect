"""
API endpoints for "project_status" package.
"""

import datetime
import os

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from webargs.flaskparser import parser
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from sqlalchemy.inspection import inspect
from flasgger.utils import swag_from
from sqlalchemy import and_
from flask_uploads import AUDIO

from app import db, c_abort, projectarchivefile
from app.base.api import AuthResource
from app.base import constants as APP
from app.base.schemas import BaseCommonSchema
from app.common.helpers import store_file
from app.resources.accounts import constants as ACCOUNT
from app.toolkit_resources.project_status.models import ProjectStatus
from app.toolkit_resources.project_status.schemas import (
    ProjectStatusSchema, ProjectStatusReadArgsSchema)

from app.toolkit_resources.projects import constants as PROJECT

from queueapp.toolkits.email_tasks import send_order_placed_email


class ProjectStatusAPI(AuthResource):
    """
    CRUD API for managing project_status
    """

    @swag_from('swagger_docs/project_status_post.yml')
    def post(self):
        """
        Create a project status
        """
        project_schema = ProjectStatusSchema()
        # get the json data from the request
        json_data = request.form
        if not json_data:
            c_abort(400)

        try:
            # get data from query string using parsing
            input_data = parser.parse(
                BaseCommonSchema(), locations=('querystring',))
            # validate and deserialize input into object
            data, errors = project_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()

        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # DETAIL:  Key (project_id, lower(parent_parameter_name::text),
                # lower(parameter_name::text))=(6, contents page,
                # list of contents) already exists.
                msg = e.orig.diag.message_detail
                column = ', '.join(
                    [s.split(':')[0].split(',')[0] for s in msg.split(
                        '(')[1:4:1]])
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (project_type_id)=(33) is not present in /
                # table "ref_project_type".
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

        return {'message': 'ProjectStatus added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @swag_from('swagger_docs/project_status_put.yml')
    def put(self, row_id):
        """
        Update a project
        """
        project_put_schema = ProjectStatusSchema()
        # first find model
        model = None
        try:
            model = ProjectStatus.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='ProjectStatus id: %s does not exist' %
                                     str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)

        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        # get the json data from the request
        json_data = request.form
        if not json_data:
            c_abort(400)

        try:
            # get data from query string using parsing
            input_data = parser.parse(
                BaseCommonSchema(), locations=('querystring',))
            # validate and deserialize input
            data, errors = project_put_schema.load(
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
                # DETAIL:  Key (project_id, lower(parent_parameter_name::text),
                # lower(parameter_name::text))=(6, contents page,
                # list of contents) already exists.
                msg = e.orig.diag.message_detail
                column = ', '.join(
                    [s.split(':')[0].split(',')[0] for s in msg.split(
                        '(')[1:4:1]])
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            elif APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (project_type_id)=(33) is not present in /
                # table "ref_project_type".
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
        return {'message': 'Updated ProjectStatus id: %s' % str(row_id)}, 200

    @swag_from('swagger_docs/project_status_delete.yml')
    def delete(self, row_id):
        """
        Delete a project
        """
        model = None
        try:
            # first find model
            model = ProjectStatus.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='ProjectStatus id: %s does not exist' %
                        str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
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

    @swag_from('swagger_docs/project_status_get.yml')
    def get(self, row_id):
        """
        Get a project by id
        """

        model = None
        try:
            # first find model
            model = ProjectStatus.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='ProjectStatus id: %s does not exist' %
                        str(row_id))
            result = ProjectStatusSchema().dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data}, 200


class ProjectStatusListAPI(AuthResource):
    """
    Read API for project lists, i.e, more than 1 project
    """
    model_class = ProjectStatus

    def __init__(self, *args, **kwargs):
        super(ProjectStatusListAPI, self).__init__(*args, **kwargs)

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

    @swag_from('swagger_docs/project_status_get_list.yml')
    def get(self):
        """
        Get the list
        """
        project_read_schema = ProjectStatusReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            project_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(ProjectStatus), operator)
            # making a copy of the main output schema
            project_schema = ProjectStatusSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                project_schema = ProjectStatusSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching project_status found')
            result = project_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
