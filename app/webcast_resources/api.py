"""
Webcast resources apis
"""

from flask import Blueprint

from app import CustomBaseApi
from app.webcast_resources.webcast_questions.api import (
    WebcastQuestionAPI, WebcastQuestionListAPI)

from app.webcast_resources.webcast_invitees.api import (
    WebcastInviteeAPI, WebcastInviteeListAPI, WebcastInviteeRegisterAPI)

from app.webcast_resources.webcast_attendees.api import (
    WebcastAttendeeAPI, WebcastAttendeeListAPI)

from app.webcast_resources.webcasts.api import (
    WebcastAPI, WebcastListAPI, WebcastCancelledAPI,
    WebcastConfereceAttendeeAPI, ReSendMailToWebcastInvitee)

from app.webcast_resources.webcast_participants.api import (
    WebcastParticipantAPI, WebcastParticipantListAPI)

from app.webcast_resources.webcast_answers.api import (
    WebcastAnswerAPI, WebcastAnswerListAPI)

from app.webcast_resources.webcast_settings.api import (
    WebcastSettingAPI, WebcastSettingListAPI)

from app.webcast_resources.webcast_rsvps.api import (
    WebcastRSVPAPI, WebcastRSVPListAPI)

from app.webcast_resources.webcast_hosts.api import (
    WebcastHostAPI, WebcastHostListAPI)
from app.webcast_resources.webcast_stats.api import (
    WebcastStatsAPI, WebcastStatsListAPI, WebcastStatsOverallAPI)

webcast_api_bp = Blueprint('webcast_api', __name__,
                           url_prefix='/api/webcast/v1.0')
webcast_api = CustomBaseApi(webcast_api_bp)

# webcast questions
webcast_api.add_resource(WebcastQuestionListAPI, '/webcast-questions')
webcast_api.add_resource(WebcastQuestionAPI, '/webcast-questions',
                         methods=['POST'], endpoint='webcastquestionpostapi')
webcast_api.add_resource(WebcastQuestionAPI, '/webcast-questions/<int:row_id>',
                         methods=['GET', 'PUT', 'DELETE'])
# webcast
webcast_api.add_resource(WebcastAPI, '/webcast', methods=['POST'],
                         endpoint='webcastpostapi')
webcast_api.add_resource(WebcastAPI, '/webcast/<int:row_id>',
                         methods=['PUT', 'GET', 'DELETE'])
webcast_api.add_resource(WebcastListAPI, '/webcast')
webcast_api.add_resource(WebcastCancelledAPI, '/webcast-cancel/<int:row_id>',
                         methods=['PUT'])
webcast_api.add_resource(
    WebcastConfereceAttendeeAPI, '/webcast-conference-attendees/<int:row_id>',
    methods=['PUT'])

# webcast invitee
webcast_api.add_resource(WebcastInviteeListAPI, '/webcast-invitees')
webcast_api.add_resource(WebcastInviteeAPI, '/webcast-invitees',
                         methods=['POST'], endpoint='webcastinviteepostapi')
webcast_api.add_resource(WebcastInviteeAPI, '/webcast-invitees/<int:row_id>',
                         methods=['GET', 'PUT', 'DELETE'])

# webcast participant
webcast_api.add_resource(WebcastParticipantListAPI, '/webcast-participants')
webcast_api.add_resource(WebcastParticipantAPI, '/webcast-participants',
                         methods=['POST'],
                         endpoint='webcastparticipantpostapi')
webcast_api.add_resource(WebcastParticipantAPI,
                         '/webcast-participants/<int:row_id>',
                         methods=['PUT', 'GET', 'DELETE'])

# webcast answers
webcast_api.add_resource(WebcastAnswerListAPI, '/webcast-answers')
webcast_api.add_resource(WebcastAnswerAPI, '/webcast-answers',
                         methods=['POST'], endpoint='webcastanswerpostapi')
webcast_api.add_resource(WebcastAnswerAPI, '/webcast-answers/<int:row_id>',
                         methods=['GET', 'PUT', 'DELETE'])

# webcast attendees
webcast_api.add_resource(WebcastAttendeeListAPI, '/webcast-attendees')
webcast_api.add_resource(WebcastAttendeeAPI, '/webcast-attendees',
                         methods=['POST'],
                         endpoint='webcastattendeepostapi')
webcast_api.add_resource(
    WebcastAttendeeAPI, '/webcast-attendees/<int:row_id>',
    methods=['GET', 'PUT', 'DELETE'])

# webcast Setting
webcast_api.add_resource(WebcastSettingAPI, '/webcast-settings',
                         methods=['POST'], endpoint='webcastsettingpostapi')
webcast_api.add_resource(WebcastSettingAPI, '/webcast-settings/<int:row_id>',
                         methods=['PUT', 'GET', 'DELETE'])
webcast_api.add_resource(WebcastSettingListAPI, '/webcast-settings')

# webcast rsvp
webcast_api.add_resource(WebcastRSVPListAPI, '/webcast-rsvps')
webcast_api.add_resource(WebcastRSVPAPI, '/webcast-rsvps', methods=['POST'],
                         endpoint='webcastrsvppostapi')
webcast_api.add_resource(WebcastRSVPAPI, '/webcast-rsvps/<int:row_id>',
                         methods=['PUT', 'GET', 'DELETE'])

# webcast host
webcast_api.add_resource(WebcastHostListAPI, '/webcast-hosts')
webcast_api.add_resource(WebcastHostAPI, '/webcast-hosts', methods=['POST'],
                         endpoint='webcasthostpostapi')
webcast_api.add_resource(WebcastHostAPI, '/webcast-hosts/<int:row_id>',
                         methods=['PUT', 'GET', 'DELETE'])

# webcast stats
webcast_api.add_resource(WebcastStatsListAPI, '/webcast-stats')
webcast_api.add_resource(WebcastStatsAPI, '/webcast-stats/<row_id>',
                         methods=['GET'])
webcast_api.add_resource(WebcastStatsOverallAPI, '/webcast-stats-overall')

# webcast register
webcast_api.add_resource(
    WebcastInviteeRegisterAPI, '/webcast-invitees/register', methods=['POST'],
    endpoint='webcastinviteeregisterpostapi')
webcast_api.add_resource(
    WebcastInviteeRegisterAPI, '/webcast-invitees/register/<int:row_id>',
    methods=['DELETE'])

#webcast resend mail to invitees
webcast_api.add_resource(ReSendMailToWebcastInvitee,
                            '/resend-invitee-emails/<int:row_id>',
                            methods=['PUT'])