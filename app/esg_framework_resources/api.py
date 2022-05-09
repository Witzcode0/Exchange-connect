"""
ECG framework resources apis
"""

from flask import Blueprint

from app import CustomBaseApi
from app.esg_framework_resources.esg_parameters.api import (
    ESGParameterAPI, ESGParameterListAPI)

esg_api_bp = Blueprint('esg_api', __name__,
                           url_prefix='/api/esg/v1.0')
esg_api = CustomBaseApi(esg_api_bp)

esg_api.add_resource(ESGParameterListAPI, '/esg-parameters')
esg_api.add_resource(ESGParameterAPI, '/esg-parameters',
                         methods=['POST'], endpoint='esgparameterspostapi')
esg_api.add_resource(ESGParameterAPI, '/esg-parameters/<int:row_id>',
                         methods=['GET', 'PUT', 'DELETE'])