"""
API endpoints for "projects parameter" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from flasgger.utils import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.toolkit_resources.project_parameters.models import ProjectParameter
from app.toolkit_resources.project_parameters.schemas import (
    ProjectParameterSchema, ProjectParameterReadArgsSchema)
from app.base import constants as APP
from app.toolkit_resources.projects.models import Project
from app.toolkit_resources.projects.helpers import calculate_status


class ProjectParameterAPI(AuthResource):
    """
    CRUD API for managing Project Parameters
    """
    @swag_from('swagger_docs/project_parameters_post.yml')
    def post(self):
        """
        Create a Project Parameters
        """
        projectparameter_schema = ProjectParameterSchema()
        # get the form data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            projectparameter_schema._validate_pp_name = True
            data, errors = projectparameter_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            # for account_id of project
            project = Project.query.get(data.project_id)
            data.account_id = project.account_id
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
                # Key (project_id)=(25) is not present in table "project".
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
        return {'message': 'Project Parameter added: %s' % str(
            data.row_id), 'row_id': data.row_id}, 201

    @swag_from('swagger_docs/project_parameters_put.yml')
    def put(self, row_id):
        """
        Update a Project Parameters
        """
        projectparameter_schema = ProjectParameterSchema()
        # first find model
        model = None
        try:
            model = ProjectParameter.query.get(row_id)
            if model is None:
                c_abort(404, message='Project Parameter id:'
                        ' %s does not exist' % str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
        except HTTPException as e:
            raise e
        except Exception as e:
            abort(500)

        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input
            projectparameter_schema._validate_pp_name = True
            data, errors = projectparameter_schema.load(
                json_data, instance=model, partial=True)

            if errors:
                c_abort(422, errors=errors)
            # no errors, so update data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()
            # status calculate and update in project table
            # calculate_status(data.project_id)
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
                # Key (project_id)=(105) is not present in table "project"
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
        return {'message': 'Updated Project Parameter id: %s'
                % str(row_id)}, 200

    @swag_from('swagger_docs/project_parameters_delete.yml')
    def delete(self, row_id):
        """
        Delete a Project Parameters
        """
        model = None
        try:
            # first find model
            model = ProjectParameter.query.get(row_id)
            if model is None:
                c_abort(404, message='Project Parameter '
                        'id: %s does not exist' % str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            # to be used before status calculation
            proj_id = model.project_id
            db.session.delete(model)
            db.session.commit()
            # status calculate and update in project table
            calculate_status(proj_id)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            abort(500)
        return {}, 204

    @swag_from('swagger_docs/project_parameters_get.yml')
    def get(self, row_id):
        """
        Get a Project Parameter by id
        """
        model = None
        try:
            # first find model
            model = ProjectParameter.query.get(row_id)
            if model is None:
                c_abort(404, message='Project Parameter id:'
                        ' %s does not exist' % str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            result = ProjectParameterSchema(
                exclude=ProjectParameterSchema._default_exclude_fields).dump(
                model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class ProjectParameterListAPI(AuthResource):
    """
    Read API for Project Parameter lists, i.e, more than 1 project
    """
    model_class = ProjectParameter

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['project', 'creator', 'account']
        super(ProjectParameterListAPI, self).__init__(*args, **kwargs)

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

    @swag_from('swagger_docs/project_parameters_get_list.yml')
    def get(self):
        """
        Get the list
        """
        projectparameter_read_schema = ProjectParameterReadArgsSchema(
            strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            projectparameter_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(ProjectParameter), operator)
            # making a copy of the main output schema
            projectparameter_schema = ProjectParameterSchema(
                exclude=ProjectParameterSchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                projectparameter_schema = ProjectParameterSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching project parameters found')
            result = projectparameter_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            abort(500)
        return {'results': result.data, 'total': total}, 200
