"""
helpdesk resources apis
"""
from flask import Blueprint

from app import CustomBaseApi

from app.helpdesk_resources.help_comments.api import (
    HelpCommentAPI, HelpCommentListAPI)

from app.helpdesk_resources.help_tickets.api import (
    HelpTicketAPI, HelpTicketListAPI)


helpdesk_api_bp = Blueprint('helpdesk_api', __name__,
                            url_prefix='/api/helpdesk/v1.0')
helpdesk_api = CustomBaseApi(helpdesk_api_bp)

# help tickets
helpdesk_api.add_resource(HelpTicketListAPI, '/tickets')
helpdesk_api.add_resource(HelpTicketAPI, '/tickets/<int:row_id>',
                          methods=['GET', 'PUT', 'DELETE'])
helpdesk_api.add_resource(HelpTicketAPI, '/tickets',
                          methods=['POST'], endpoint='helpticketpostapi')

# help ticket comments
helpdesk_api.add_resource(HelpCommentListAPI, '/comments')
helpdesk_api.add_resource(HelpCommentAPI, '/comments/<int:row_id>',
                          methods=['GET', 'PUT', 'DELETE'])
helpdesk_api.add_resource(HelpCommentAPI, '/comments',
                          methods=['POST'], endpoint='helpcommentpostapi')
