"""
API endpoints for "permissions" package.
"""

from flask import request, current_app
from flask_restful import abort
from werkzeug.exceptions import Forbidden, HTTPException
from sqlalchemy.orm import load_only
from flasgger import swag_from

from app import db, c_abort
from app.resources.permissions.models import Permission
from app.resources.permissions.schemas import (
    PermissionSchema, PermissionEditSchema)
from app.base.api import AuthResource
from app.base import constants as APP
from app.resources.permissions.schemas import PermissionReadArgSchema
from app.auth.decorators import role_permission_required
from app.resources.roles import constants as ROLE


class PermissionAPI(AuthResource):
    """
    Post API for contact us inquiries
    """

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    @swag_from('swagger_docs/permission_post.yml')
    def post(self):
        """
        Create a permission
        """
        permission_schema = PermissionSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = permission_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (country_id, state_id, city_name)=(1, 1, Hyd)
                # already exists.
                column = e.orig.diag.message_detail.split('(')[2].split(':')[0]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Permission added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    @swag_from('swagger_docs/permission_put.yml')
    def put(self, row_id):
        """
        Update permission by row_id
        """
        permission_schema = PermissionEditSchema()
        model = None
        try:
            model = Permission.query.get(row_id)
            if model is None:
                c_abort(404, message='Permission id: %s'
                                     ' does not exist' % str(row_id))
        except Forbidden as e:
            raise e
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
            data, errors = permission_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Updated Permission id: %s' %
                           str(row_id)}, 200

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    @swag_from('swagger_docs/permission_delete.yml')
    def delete(self, row_id):
        """
        Delete a permission by row_id
        """
        try:
            # first find model
            model = Permission.query.get(row_id)
            if model is None:
                c_abort(404, message='Permission id: %s'
                                     ' does not exist' % str(row_id))
            # if model is found, and not yet deleted, delete it
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

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    @swag_from('swagger_docs/permission_get.yml')
    def get(self, row_id):
        """
        Get a permission by id
        """
        result = None
        permission_schema = PermissionSchema()
        try:
            # first find model
            model = Permission.query.get(row_id)
            if model is None:
                c_abort(404, message='Permission id: %s'
                                     ' does not exist' % str(row_id))
            result = permission_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class PermissionListAPI(AuthResource):
    """
    Read API for permission lists, i.e, more than 1 permission
    """
    model_class = Permission

    def __init__(self, *args, **kwargs):
        super(
            PermissionListAPI, self).__init__(*args, **kwargs)

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

        query = self._build_final_query(
            query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    @swag_from('swagger_docs/permission_get_list.yml')
    def get(self):
        """
        Get the list of permission by admin
        """
        # schema for reading get arguments
        permission_read_schema = PermissionReadArgSchema(
            strict=True)
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            permission_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Permission),
                                 operator)
            # making a copy of the main output schema
            permission_schema = PermissionSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                permission_schema = PermissionSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching permissions found')
            result = permission_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
