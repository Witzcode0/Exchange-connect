"""
API endpoints for "project_designer" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from flasgger.utils import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.toolkit_resources.project_designers.models import ProjectDesigner
from app.toolkit_resources.project_designers.schemas import (
    ProjectDesignerSchema, ProjectDesignerReadArgsSchema)
from app.base import constants as APP
from app.toolkit_resources.project_status.models import ProjectStatus

from queueapp.toolkits.email_tasks import send_project_assigned_emails

class ProjectDesignerAPI(AuthResource):
    """
    CRUD API for managing project_designers
    """

    #@swag_from('swagger_docs/project_designers_post.yml')
    def post(self):
        """
        Create a project_designer
        """

        project_designer_schema = ProjectDesignerSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = project_designer_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()
            project = data.designed_project
            # changing status of project to "proj_assigned"
            if not project.status_id:
                project.status_id = ProjectStatus.query.filter_by(
                    code="proj_assigned").first().row_id
                db.session.add(project)
                db.session.commit()
            send_project_assigned_emails.s(
                True, project.row_id,g.current_user['row_id'], [],
                [data.designer_id]).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (project_id, designer_id)=(17, 2) already exists.
                column = e.orig.diag.message_detail.split('(')[1].split(')')[0]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            elif APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (designer_id)=(25) is not present in \
                # table "project_designer".
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

        return {'message': 'Project Designer added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    #@swag_from('swagger_docs/project_designers_put.yml')
    def put(self, row_id):
        """
        Update a project_designer
        """

        project_designer_schema = ProjectDesignerSchema()
        # first find model
        model = None
        try:
            model = ProjectDesigner.query.get(row_id)
            if model is None:
                c_abort(404, message='Project Designer id: %s does not exist' %
                                     str(row_id))
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
            data, errors = project_designer_schema.load(
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
                # Key (project_id, designer_id)=(17, 2) already exists.
                column = e.orig.diag.message_detail.split('(')[1].split(')')[0]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            elif APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (designer_id)=(25) is not present in \
                # table "project_designer".
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
        return {'message': 'Updated Project Designer id: %s' % str(row_id)}, 200

    #@swag_from('swagger_docs/project_designers_delete.yml')
    def delete(self, row_id):
        """
        Delete a project_designer
        """

        model = None
        try:
            # first find model
            model = ProjectDesigner.query.get(row_id)
            if model is None:
                c_abort(404, message='Project Designer id: %s does not exist' %
                                     str(row_id))
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

    #@swag_from('swagger_docs/project_designers_get.yml')
    def get(self, row_id):
        """
        Get a project_designer by id
        """

        project_designer_schema = ProjectDesignerSchema()
        model = None
        try:
            # first find model
            model = ProjectDesigner.query.get(row_id)
            if model is None:
                c_abort(404, message='Project Designer id: %s does not exist' %
                                     str(row_id))
            result = project_designer_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class ProjectDesignerListAPI(AuthResource):
    """
    Read API for project_designer lists, i.e, more than 1 project_designer
    """

    model_class = ProjectDesigner

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['assigned_project', 'designer']
        super(ProjectDesignerListAPI, self).__init__(*args, **kwargs)

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

    #@swag_from('swagger_docs/project_designers_get_list.yml')
    def get(self):
        """
        Get the list
        """

        project_designer_read_schema = ProjectDesignerReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            project_designer_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(ProjectDesigner), operator)
            # making a copy of the main output schema
            project_designer_schema = ProjectDesignerSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                project_designer_schema = ProjectDesignerSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching project_designers found')
            result = project_designer_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
