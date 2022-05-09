"""
API endpoints for "countries" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from flasgger.utils import swag_from

from app import db, c_abort
from app.base.api import AuthResource, BaseResource
from app.auth.decorators import role_permission_required
from app.resources.countries.models import Country
from app.resources.countries.schemas import (
    CountrySchema, CountryReadArgsSchema)
from app.base import constants as APP
from app.resources.roles import constants as ROLE


class CountryAPI(AuthResource):
    """
    CRUD API for managing countries
    """

    @role_permission_required(perms=[ROLE.EPT_NU])
    @swag_from('swagger_docs/country_post.yml')
    def post(self):
        """
        Create an country
        """
        country_schema = CountrySchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = country_schema.load(json_data)
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
                # Key (lower(name::text))=(abc) already exists.
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

        return {'message': 'Country added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @role_permission_required(perms=[ROLE.EPT_NU])
    @swag_from('swagger_docs/country_put.yml')
    def put(self, row_id):
        """
        Update an country
        """
        country_schema = CountrySchema()
        # first find model
        model = None
        try:
            model = Country.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='country id: %s does not exist' %
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
            data, errors = country_schema.load(
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
                # Key (lower(name::text))=(abc) already exists.
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
        return {'message': 'Updated Country id: %s' % str(row_id)}, 200

    @swag_from('swagger_docs/country_delete.yml')
    def delete(self, row_id):
        """
        Delete an country by id
        """
        model = None
        try:
            # first find model
            model = Country.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Country id: %s does not exist' %
                                     str(row_id))
            model.deleted = True
            model.updated_by = g.current_user['row_id']
            db.session.add(model)
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

    @swag_from('swagger_docs/country_get.yml')
    def get(self, row_id):
        """
        Get an country by id
        """
        model = None
        try:
            # first find model
            model = Country.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Country id: %s does not exist' %
                                     str(row_id))
            result = CountrySchema(
                exclude=CountrySchema._default_exclude_fields).dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class CountryListAPI(BaseResource):
    """
    Read API for country lists, i.e, more than 1 country
    """
    model_class = Country

    def __init__(self, *args, **kwargs):
        super(CountryListAPI, self).__init__(*args, **kwargs)

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

    @swag_from('swagger_docs/country_get_list.yml')
    def get(self):
        """
        Get the list
        """
        country_read_schema = CountryReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            country_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Country), operator)
            # making a copy of the main output schema
            country_schema = CountrySchema(
                exclude=CountrySchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                country_schema = CountrySchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching countries found')
            result = country_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
