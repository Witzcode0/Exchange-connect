"""
disclosure enhancements resources apis
"""
from flask import Blueprint

from app import CustomBaseApi

from app.disclosure_enhancement_resources.de_peer_groups.api import (
    DePeerGroupAPI, DePeerGroupListAPI)


disclosure_enhancement_api_bp = Blueprint(
    'disclosure_enhancement_api', __name__,
    url_prefix='/api/disclosure-enhancement/v1.0')
disclosure_enhancement_api = CustomBaseApi(disclosure_enhancement_api_bp)

# depeer group
disclosure_enhancement_api.add_resource(
    DePeerGroupAPI, '/de-peer-groups', methods=['POST'],
    endpoint='depeergrouppostapi')
disclosure_enhancement_api.add_resource(DePeerGroupListAPI, '/de-peer-groups')
disclosure_enhancement_api.add_resource(
    DePeerGroupAPI, '/de-peer-groups/<int:row_id>',
    methods=['GET', 'PUT', 'DELETE'])
