"""
API endpoints for "admin domain_configs" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.base import constants as APP
from app.auth.decorators import role_permission_required
from app.domain_resources.domain_config.models import DomainConfig
from app.domain_resources.domain_config.schemas import (
    DomainConfigSchema, DomainConfigReadArgsSchema)
from app.resources.roles import constants as ROLE


class DomainConfigAPI(AuthResource):
    """
    Create, update, delete API for domain_configs
    """

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[ROLE.ERT_SU])
    @swag_from('swagger_docs/domain_config_post.yml')
    def post(self):
        """
        Create an domain_config
        """
        domain_config_schema = DomainConfigSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = domain_config_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            db.session.add(data)
            db.session.commit()

        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (lower(domain_config_name::text))=(abc) already exists.
                column = e.orig.diag.message_detail.split('(')[2].split(':')[0]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'DomainConfig added: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    @swag_from('swagger_docs/domain_config_put.yml')
    def put(self, row_id):
        """
        Update an domain_config
        """
        domain_config_schema = DomainConfigSchema()
        # first find model
        model = None
        try:
            model = DomainConfig.query.get(row_id)
            if model is None:
                c_abort(404, message='DomainConfig id: %s'
                        ' does not exist' % str(row_id))
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
            data, errors = domain_config_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)

            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (lower(domain_config_name::text))=(abc) already exists.
                column = e.orig.diag.message_detail.split('(')[2].split(':')[0]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})

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
        return {'message': 'Updated DomainConfig id: %s' %
                str(row_id)}, 200

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[ROLE.ERT_SU])
    @swag_from('swagger_docs/domain_config_delete.yml')
    def delete(self, row_id):
        """
        Delete an domain_config
        """
        try:
            # first find model
            model = DomainConfig.query.get(row_id)
            if model is None:
                c_abort(404, message='DomainConfig id: %s'
                        ' does not exist' % str(row_id))

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
    @swag_from('swagger_docs/domain_config_get.yml')
    def get(self, row_id):
        """
        Get an domain_config by id
        """
        try:
            # first find model
            model = DomainConfig.query.get(row_id)
            if model is None:
                c_abort(404, message='DomainConfig id: %s'
                        ' does not exist' % str(row_id))
            result = DomainConfigSchema().dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class DomainConfigListAPI(AuthResource):
    """
    Read API for domain_config lists, i.e, more than 1 domain_config
    """
    model_class = DomainConfig

    def __init__(self, *args, **kwargs):
        super(DomainConfigListAPI, self).__init__(*args, **kwargs)

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
        query = self._build_final_query(query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    @swag_from('swagger_docs/domain_config_get_list.yml')
    def get(self):
        """
        Get the list
        """
        domain_config_read_schema = DomainConfigReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            domain_config_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(DomainConfig), operator)
            # making a copy of the main output schema
            domain_config_schema = DomainConfigSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                domain_config_schema = DomainConfigSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching domain_configs found')
            result = domain_config_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data, 'total': total}, 200

