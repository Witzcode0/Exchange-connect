"""
API endpoints for "parsing file" package.
"""


from werkzeug.exceptions import HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.orm import load_only
from flasgger.utils import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.semidocument_resources.parsing_files.models import ParsingFile
from app.semidocument_resources.parsing_files.schemas import (
    ParsingFileSchema, ParsingFileReadArgsSchema)
from app.semidocument_resources.research_reports.models import ResearchReport


class ParsingFileListAPI(AuthResource):
    """
    Read API for library file lists, i.e, more than 1 library file
    """
    model_class = ParsingFile

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['filename_url']
        super(ParsingFileListAPI, self).__init__(*args, **kwargs)

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
        if extra_query and extra_query.get('research_report_id'):
            research_report = ResearchReport.query.get(
                extra_query['research_report_id'])
            if research_report:
                query_filters['base'].append(
                    ParsingFile.account_id ==
                    research_report.corporate_account_id)

        query = self._build_final_query(query_filters, query_session, operator)
        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/file_archive_get_list.yml')
    def get(self):
        """
        Get the list
        """
        parsing_file_read_schema = ParsingFileReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            parsing_file_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(ParsingFile), operator)
            # making a copy of the main output schema
            parsing_file_schema = ParsingFileSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                parsing_file_schema = ParsingFileSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching files found')
            result = parsing_file_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
