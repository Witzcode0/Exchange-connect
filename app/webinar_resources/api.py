"""
Webinar resources apis
"""

from flask import Blueprint

from app import CustomBaseApi
from app.webinar_resources.webinar_chats.api import (
    WebinarChatMessageAPI, WebinarChatMessageListAPI)

from app.webinar_resources.webinar_questions.api import (
    WebinarQuestionAPI, WebinarQuestionListAPI)

from app.webinar_resources.webinar_answers.api import (
    WebinarAnswerAPI, WebinarAnswerListAPI)

from app.webinar_resources.webinar_invitees.api import (
    WebinarInviteeAPI, WebinarInviteeListAPI, WebinarInviteeRegisterAPI,
    PublicWebinarRegisterAPI)

from app.webinar_resources.webinar_participants.api import (
    WebinarParticipantAPI, WebinarParticipantListAPI)

from app.webinar_resources.webinar_attendees.api import (
    WebinarAttendeeAPI, WebinarAttendeeListAPI)

from app.webinar_resources.webinar_rsvps.api import (
    WebinarRSVPAPI, WebinarRSVPListAPI)

from app.webinar_resources.webinar_hosts.api import (
    WebinarHostAPI, WebinarHostListAPI)

from app.webinar_resources.webinars.api import (
    WebinarAPI, WebinarListAPI, WebinarCancelledAPI,
    WebinarConfereceAttendeeAPI, PublicWebinarAPI, PublicWebinarListAPI,
    WebinarReminderAPI, ReSendMailToWebinarInvitee)

from app.webinar_resources.webinar_stats.api import (
    WebinarStatsAPI, WebinarStatsListAPI, WebinarStatsOverallAPI)

webinar_api_bp = Blueprint('webinar_api', __name__,
                           url_prefix='/api/webinar/v1.0')
webinar_api = CustomBaseApi(webinar_api_bp)

# webinar_chats
webinar_api.add_resource(WebinarChatMessageListAPI, '/webinar-chat-messages')
webinar_api.add_resource(WebinarChatMessageAPI, '/webinar-chat-messages',
                         methods=['POST'], endpoint='webinarchatpostapi')
webinar_api.add_resource(WebinarChatMessageAPI,
                         '/webinar-chat-messages/<int:row_id>',
                         methods=['GET', 'PUT', 'DELETE'])

# webinar questions
webinar_api.add_resource(WebinarQuestionListAPI, '/webinar-questions')
webinar_api.add_resource(WebinarQuestionAPI, '/webinar-questions',
                         methods=['POST'], endpoint='webinarquestionpostapi')
webinar_api.add_resource(WebinarQuestionAPI, '/webinar-questions/<int:row_id>',
                         methods=['GET', 'PUT', 'DELETE'])

# webinar answers
webinar_api.add_resource(WebinarAnswerListAPI, '/webinar-answers')
webinar_api.add_resource(WebinarAnswerAPI, '/webinar-answers',
                         methods=['POST'], endpoint='webinaranswerpostapi')
webinar_api.add_resource(WebinarAnswerAPI, '/webinar-answers/<int:row_id>',
                         methods=['GET', 'PUT', 'DELETE'])

# webinar invitee
webinar_api.add_resource(WebinarInviteeListAPI, '/webinar-invitees')
webinar_api.add_resource(WebinarInviteeAPI, '/webinar-invitees',
                         methods=['POST'], endpoint='webinarinviteepostapi')
webinar_api.add_resource(WebinarInviteeAPI, '/webinar-invitees/<int:row_id>',
                         methods=['GET', 'PUT', 'DELETE'])
webinar_api.add_resource(
    WebinarInviteeRegisterAPI, '/webinar-invitees/register',
    methods=['POST'], endpoint='webinarinviteeregisterpostapi')
webinar_api.add_resource(
    WebinarInviteeRegisterAPI, '/webinar-invitees/register/<int:row_id>',
    methods=['DELETE'])
webinar_api.add_resource(
    PublicWebinarRegisterAPI, '/public-webinar-invitees/register',
    methods=['POST'])

# webinar participants
webinar_api.add_resource(WebinarParticipantListAPI, '/webinar-participants')
webinar_api.add_resource(WebinarParticipantAPI, '/webinar-participants',
                         methods=['POST'],
                         endpoint='webinarparticipantpostapi')
webinar_api.add_resource(WebinarParticipantAPI,
                         '/webinar-participants/<int:row_id>',
                         methods=['PUT', 'GET', 'DELETE'])

# webinar attendees
webinar_api.add_resource(WebinarAttendeeListAPI, '/webinar-attendees')
webinar_api.add_resource(WebinarAttendeeAPI, '/webinar-attendees',
                         methods=['POST'],
                         endpoint='webinarattendeepostapi')
webinar_api.add_resource(
    WebinarAttendeeAPI, '/webinar-attendees/<int:row_id>',
    methods=['GET', 'PUT', 'DELETE'])

# webinar rsvp
webinar_api.add_resource(WebinarRSVPListAPI, '/webinar-rsvps')
webinar_api.add_resource(WebinarRSVPAPI, '/webinar-rsvps', methods=['POST'],
                         endpoint='webinarrsvppostapi')
webinar_api.add_resource(WebinarRSVPAPI, '/webinar-rsvps/<int:row_id>',
                         methods=['PUT', 'GET', 'DELETE'])

# webinar host
webinar_api.add_resource(WebinarHostListAPI, '/webinar-hosts')
webinar_api.add_resource(WebinarHostAPI, '/webinar-hosts', methods=['POST'],
                         endpoint='webinarhostpostapi')
webinar_api.add_resource(WebinarHostAPI, '/webinar-hosts/<int:row_id>',
                         methods=['PUT', 'GET', 'DELETE'])

# webinar
webinar_api.add_resource(WebinarAPI, '/webinar', methods=['POST'],
                         endpoint='webinarpostapi')
webinar_api.add_resource(WebinarAPI, '/webinar/<int:row_id>',
                         methods=['PUT', 'GET', 'DELETE'])
webinar_api.add_resource(WebinarListAPI, '/webinar')
webinar_api.add_resource(WebinarCancelledAPI, '/webinar-cancel/<int:row_id>',
                         methods=['PUT'])
webinar_api.add_resource(
    WebinarConfereceAttendeeAPI,
    '/webinar-conference-attendees/<int:row_id>', methods=['PUT'])
webinar_api.add_resource(PublicWebinarAPI, '/public-webinar/<int:row_id>',
                         methods=['GET'])
webinar_api.add_resource(PublicWebinarListAPI, '/public-webinar')

# webinar stats
webinar_api.add_resource(WebinarStatsListAPI, '/webinar-stats')
webinar_api.add_resource(WebinarStatsAPI, '/webinar-stats/<int:row_id>',
                         methods=['GET'])
webinar_api.add_resource(WebinarStatsOverallAPI, '/webinar-stats-overall')

# webinar sent reminder email
webinar_api.add_resource(WebinarReminderAPI,
                         '/sent-webinar-reminder/<int:row_id>')

#webinar resend mail to invitees
webinar_api.add_resource(ReSendMailToWebinarInvitee,
                            '/resend-invitee-emails/<int:row_id>',
                            methods=['PUT'])