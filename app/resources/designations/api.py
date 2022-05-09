"""
API endpoints for "designation" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource, BaseResource
from app.base import constants as APP
from app.resources.designations.models import Designation
from app.resources.designations.schemas import (
    DesignationSchema, DesignationReadArgsSchema)


class DesignationAPI(AuthResource):
    """
    Create, update, delete API for designation
    """
    @swag_from('swagger_docs/designation_post.yml')
    def post(self):
        """
        Create designation
        """
        designation_schema = DesignationSchema()
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = designation_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (lower(name::text))=(manager) already exists.
                column = e.orig.diag.message_detail.split('(')[2][:-9]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Designation Added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @swag_from('swagger_docs/designation_put.yml')
    def put(self, row_id):
        """
        Update designation by id
        """
        designation_schema = DesignationSchema()
        model = None
        try:
            model = Designation.query.get(row_id)
            if model is None:
                c_abort(404, message='Designation id: %s does not exist' %
                                     str(row_id))
            # only current user can change designation
            if model.created_by != g.current_user['row_id']:
                c_abort(401)
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            data, errors = designation_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.edited = True
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (lower(name::text))=(manager) already exists.
                column = e.orig.diag.message_detail.split('(')[2][:-9]
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

        return {'message': 'updated Designation response id: %s' %
                str(row_id)}, 200

    @swag_from('swagger_docs/designation_delete.yml')
    def delete(self, row_id):
        """
        Delete designation by id
        """
        model = None
        try:
            model = Designation.query.get(row_id)
            if model is None:
                c_abort(404, message='designation id: %s does not exist' %
                                     str(row_id))
            if model.created_by != g.current_user['row_id']:
                c_abort(401)

            db.session.delete(model)
            db.session.commit()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {}, 204

    @swag_from('swagger_docs/designation_get.yml')
    def get(self, row_id):
        """
        Get designation by id
        """
        designation_schema = DesignationSchema()
        model = None
        try:
            model = Designation.query.get(row_id)
            if model is None:
                c_abort(404, message='designation id: %s does not exist' %
                                     str(row_id))
            result = designation_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result}, 200


class DesignationListAPI(BaseResource):
    """
    Read API for designation lists, i.e, more than 1 designation
    """

    model_class = Designation

    def __init__(self, *args, **kwargs):
        super(DesignationListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        query_filters, extra_query, db_projection, s_projection, order, \
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)
        # build specific extra queries filters
        if extra_query:
            pass

        # #TODO: user filter used in future
        # query_filters['base'].append(
        #     Designation.created_by == g.current_user['row_id'])
        query = self._build_final_query(query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/designation_get_list.yml')
    def get(self):
        """
        Get the list
        """
        designation_read_schema = DesignationReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            designation_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Designation), operator)
            # making a copy of the main output schema
            designation_schema = DesignationSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                designation_schema = DesignationSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching designation found')
            result = designation_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data, 'total': total}, 200
