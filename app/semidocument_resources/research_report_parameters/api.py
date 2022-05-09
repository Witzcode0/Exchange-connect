"""
API endpoints for "research report parameters" package.
"""

from app.semidocument_resources.research_reports import \
    constants as RESEARCH_REPORT
from app.semidocument_resources.research_report_parameters.schemas import (
    ResearchReportParameterSchema, ResearchReportParameterReadArgsSchema)
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy import and_, func
from sqlalchemy.orm import load_only, joinedload, aliased
from werkzeug.exceptions import Forbidden, HTTPException

from app import db, c_abort, researchreportfile
from app.base.api import AuthResource
from app.common.helpers import store_file, delete_files
from app.resources.accounts import constants as ACCOUNT
from app.resources.accounts.models import Account
from app.resources.users.models import User
from app.semidocument_resources.research_report_parameters.models import (
    ResearchReportParameter, reportparameters)
from app.semidocument_resources.research_reports.models import ResearchReport


class ResearchReportParameterAPI(AuthResource):
    """
    CRUD API for research report parameter
    """

    # @swag_from('swagger_docs/research_report_post.yml')
    def post(self):
        """
        Create research report parameter parameter
        """

        research_report_param_schema = ResearchReportParameterSchema()
        # get the form data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            data, errors = research_report_param_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            db.session.add(data)
            db.session.commit()

        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Research Report Parameter Parameter created: %s' %
                           str(data.row_id), 'row_id': data.row_id}, 201

    # @swag_from('swagger_docs/corporate_announcement_put.yml')
    def put(self, row_id):
        """
        Update Research report parameter
        """
        research_report_param_schema = ResearchReportParameterSchema()

        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            model = ResearchReportParameter.query.get(row_id)
            if model is None:
                c_abort(404, message='Research Report Parameter id: %s'
                                     ' does not exist' % str(row_id))

            # validate and deserialize input
            data, errors = research_report_param_schema.load(
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

        return {'message': 'Updated Research Report Parameter id: %s' %
                           str(row_id)}, 200

    # @swag_from('swagger_docs/corporate_announcement_delete.yml')
    def delete(self, row_id):
        """
        Delete a research report parameter
        """
        try:
            # first find model
            model = ResearchReportParameter.query.get(row_id)
            if model is None:
                c_abort(404, message='Research Report Parameter id: %s'
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

    # @swag_from('swagger_docs/corporate_announcement_get.yml')
    def get(self, row_id):
        """
        Get a research report parameter by id
        """
        result = None
        try:
            # first find model
            model = ResearchReportParameter.query.get(row_id)
            if model is None:
                c_abort(404, message='Research Report Parameter id: %s'
                                     ' does not exist' % str(row_id))
            result = ResearchReportParameterSchema().dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data}, 200


class ResearchReportParameterListAPI(AuthResource):
    """
    Read API for research report parameter lists, i.e, more than 1
    """
    model_class = ResearchReportParameter

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['account']
        super(ResearchReportParameterListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        # build specific extra queries filters
        corporate_account_id = None
        research_report_id = filters.get('research_report_id')
        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)

        query = self._build_final_query(
            query_filters, query_session, operator)
        if research_report_id:
            query = query.join(
                reportparameters,
                reportparameters.c.parameter_id==ResearchReportParameter.row_id,
                ).join(
                ResearchReport,
                ResearchReport.corporate_account_id==ResearchReportParameter.account_id
            ).filter(and_(
                ResearchReport.row_id==research_report_id,
                reportparameters.c.report_id == research_report_id)).order_by(
                ResearchReportParameter.sequence)

        return query, db_projection, s_projection, order, paging

    # @swag_from('swagger_docs/corporate_announcement_get_list.yml')
    def get(self):
        """
        Get the list
        """
        total = 0
        research_report_read_schema = ResearchReportParameterReadArgsSchema(strict=True)
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            research_report_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(ResearchReportParameter),
                                 operator)
            # making a copy of the main output schema
            research_report_param_schema = ResearchReportParameterSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                research_report_param_schema = ResearchReportParameterSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404,
                        message='No matching research report parameters found')

            result = research_report_param_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class ResearchReportParameterBulkAPI(AuthResource):

    def put(self):
        """
        update multiple research report parameters
        """
        research_report_param_schema = ResearchReportParameterSchema()

        # get the json data from the request
        json_data = request.get_json()
        if not json_data or not json_data.get('research_report_parameters'):
            c_abort(400)

        try:
            for param in json_data['research_report_parameters']:
                model = ResearchReportParameter.query.get(param['row_id'])
                if model is None:
                    c_abort(404, message='Research Report Parameter id: %s'
                                         ' does not exist' % str(param['row_id']))

                # validate and deserialize input
                data, errors = research_report_param_schema.load(
                    param, instance=model, partial=True)
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

        return {'message': 'Updated Research Report Parameters.'}, 200
