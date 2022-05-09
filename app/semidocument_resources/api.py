"""
semi documentation apis
"""

from flask import Blueprint

from app import CustomBaseApi

from app.semidocument_resources.research_reports.api import (
    ResearchReportAPI, ResearchReportListAPI)
from app.semidocument_resources.research_report_parameters.api import (
    ResearchReportParameterAPI, ResearchReportParameterListAPI,
    ResearchReportParameterBulkAPI)
from app.semidocument_resources.parsing_files.api import ParsingFileListAPI

semi_documentation_api_bp = Blueprint(
    'semi_documentation_api', __name__,
    url_prefix='/api/semi-documentation/v1.0')
semi_documentation_api = CustomBaseApi(semi_documentation_api_bp)

# Research Report
semi_documentation_api.add_resource(ResearchReportListAPI, '/research-reports')
semi_documentation_api.add_resource(
    ResearchReportAPI, '/research-reports', methods=['POST'], endpoint='researchreportpostapi')
semi_documentation_api.add_resource(
    ResearchReportAPI, '/research-reports/<int:row_id>', methods=[
        'PUT', 'GET', 'DELETE'])

# research report parameter apis
semi_documentation_api.add_resource(
    ResearchReportParameterListAPI, '/research-report-parameters')
semi_documentation_api.add_resource(
    ResearchReportParameterAPI, '/research-report-parameters',
    methods=['POST'], endpoint='researchreportparameterspostapi')
semi_documentation_api.add_resource(
    ResearchReportParameterAPI, '/research-report-parameters/<int:row_id>',
    methods=['PUT', 'GET', 'DELETE'])
semi_documentation_api.add_resource(
    ResearchReportParameterBulkAPI, '/research-report-parameters-bulk',
    methods=['PUT'])

semi_documentation_api.add_resource(ParsingFileListAPI, '/parsing-files')
