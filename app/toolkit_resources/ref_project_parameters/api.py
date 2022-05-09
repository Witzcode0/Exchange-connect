"""
API endpoints for "reference project parameters" package.
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
from app.toolkit_resources.ref_project_parameters.models import (
    RefProjectParameter)
from app.toolkit_resources.ref_project_parameters.schemas import (
    RefProjectParameterSchema, RefProjectParameterReadArgsSchema)


class RefProjectParameterAPI(AuthResource):
    """
    CRUD API for managing reference project parameters
    """
    @swag_from('swagger_docs/ref_project_parameters_post.yml')
    def post(self):
        """
        Create a reference project parameter
        """
        ref_project_parameter_schema = RefProjectParameterSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = ref_project_parameter_schema.load(json_data)
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
                # Key (project_type_id, parent_parameter_name,
                # parameter_name)=(3, presentations, earnings) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            elif APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (project_type_id)=(5) is not present
                # in table "ref_project_type".
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

        return {'message': 'Reference Project Parameter added: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201

    @swag_from('swagger_docs/ref_project_parameters_put.yml')
    def put(self, row_id):
        """
        Update a reference project parameter
        """
        ref_project_parameter_schema = RefProjectParameterSchema()
        # first find model
        model = None
        try:
            model = RefProjectParameter.query.get(row_id)
            if model is None:
                c_abort(
                    404,
                    message='Reference Project Parameter id: ' +
                    '%s does not exist' % str(row_id))
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
            data, errors = ref_project_parameter_schema.load(
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
                # Key (project_type_id, parent_parameter_name,
                # parameter_name)=(3, presentations, earnings) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            elif APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (project_type_id)=(5) is not present
                # in table "ref_project_type".
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
        return {'message': 'Updated Reference Project Parameter id: %s' %
                str(row_id)}, 200

    @swag_from('swagger_docs/ref_project_parameters_delete.yml')
    def delete(self, row_id):
        """
        Delete a reference project parameter
        """
        model = None
        try:
            # first find model
            model = RefProjectParameter.query.get(row_id)
            if model is None:
                c_abort(
                    404,
                    message='Reference Project Parameter id: ' +
                    '%s does not exist' % str(row_id))
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

    @swag_from('swagger_docs/ref_project_parameters_get.yml')
    def get(self, row_id):
        """
        Get a reference project parameter by id
        """
        ref_project_parameter_schema = RefProjectParameterSchema()
        model = None
        try:
            # first find model
            model = RefProjectParameter.query.get(row_id)
            if model is None:
                c_abort(
                    404,
                    message='Reference Project Parameter id: ' +
                    '%s does not exist' % str(row_id))
            result = ref_project_parameter_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class RefProjectParameterListAPI(AuthResource):
    """
    Read API for reference project parameter lists, i.e, more than 1 project
    """
    model_class = RefProjectParameter

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['ref_project_type']
        super(RefProjectParameterListAPI, self).__init__(*args, **kwargs)

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

    @swag_from('swagger_docs/ref_project_parameters_get_list.yml')
    def get(self):
        """
        Get the list
        """
        ref_project_parameter_read_schema = RefProjectParameterReadArgsSchema(
            strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            ref_project_parameter_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(
                    filters, pfields, sort, pagination, db.session.query(
                        RefProjectParameter), operator)
            # making a copy of the main output schema
            ref_project_parameter_schema = RefProjectParameterSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                ref_project_parameter_schema = RefProjectParameterSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(
                    404,
                    message='No matching reference project parameters found')
            result = ref_project_parameter_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
