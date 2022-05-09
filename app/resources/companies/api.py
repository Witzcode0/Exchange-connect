"""
API endpoints for "companies" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from sqlalchemy.inspection import inspect
from flasgger.utils import swag_from

from app import db, c_abort
from app.base.api import AuthResource, BaseResource
from app.base import constants as APP
from app.resources.sectors.models import Sector
from app.resources.industries.models import Industry
from app.resources.companies.models import Company
from app.resources.companies.schemas import (
    CompanySchema, CompanyReadArgsSchema)


class CompanyAPI(AuthResource):
    """
    CRUD API for managing companies
    """

    @swag_from('swagger_docs/company_post.yml')
    def post(self):
        """
        Create an company
        """
        company_schema = CompanySchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = company_schema.load(json_data)
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

        return {'message': 'Company added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @swag_from('swagger_docs/company_put.yml')
    def put(self, row_id):
        """
        Update an company
        """
        company_schema = CompanySchema()
        # first find model
        model = None
        try:
            model = Company.query.get(row_id)
            if model is None:
                c_abort(404, message='Company id: %s does not exist' %
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
            data, errors = company_schema.load(
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
        return {'message': 'Updated Company id: %s' % str(row_id)}, 200

    @swag_from('swagger_docs/company_delete.yml')
    def delete(self, row_id):
        """
        Delete an company by id
        """
        model = None
        try:
            # first find model
            model = Company.query.get(row_id)
            if model is None:
                c_abort(404, message='Company id: %s does not exist' %
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

    @swag_from('swagger_docs/company_get.yml')
    def get(self, row_id):
        """
        Get an company by id
        """
        company_schema = CompanySchema()
        model = None
        try:
            # first find model
            model = Company.query.get(row_id)
            if model is None:
                c_abort(404, message='Company id: %s does not exist' %
                                     str(row_id))
            result = company_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class CompanyListAPI(BaseResource):
    """
    Read API for company lists, i.e, more than 1 company
    """
    model_class = Company

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['creator', 'sector', 'industry']
        super(CompanyListAPI, self).__init__(*args, **kwargs)

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
        mapper = inspect(Company)
        # build specific extra queries filters
        if extra_query:
            pass

        if 'sector' in sort['sort_by']:
            sort['sort_by'].remove('sector')
            sort['sort_by'].append('name')
            mapper = inspect(Sector)
        elif 'industry' in sort['sort_by']:
            sort['sort_by'].remove('industry')
            sort['sort_by'].append('name')
            mapper = inspect(Industry)
        if sort:
            sort_fxn = 'asc'
            if sort['sort'] == 'dsc':
                sort_fxn = 'desc'
            for sby in sort['sort_by']:
                if sby in mapper.columns:
                    order.append(getattr(mapper.columns[sby], sort_fxn)())

        query = self._build_final_query(query_filters, query_session, operator)

        query = query.join(
            Sector, Sector.row_id == Company.sector_id, isouter=True).join(
            Industry, Industry.row_id == Company.industry_id, isouter=True)

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/company_get_list.yml')
    def get(self):
        """
        Get the list
        """
        company_read_schema = CompanyReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            company_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Company), operator)
            # making a copy of the main output schema
            company_schema = CompanySchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                company_schema = CompanySchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching companies found')
            result = company_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
