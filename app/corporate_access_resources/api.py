"""
Corporate access resources apis
"""

from flask import Blueprint

from app import CustomBaseApi

from app.corporate_access_resources.corporate_access_event_rsvps.api import (
    CorporateAccessEventRSVPAPI, CorporateAccessEventRSVPListAPI)

from app.corporate_access_resources.corporate_access_event_invitees.api \
    import (CorporateAccessEventInviteeAPI, CorporateAccessEventInviteeListAPI,
            CorporateAccessEventInviteeJoinedAPI,
            CorporateAccessEventInviteeRegisterAPI,
            CorporateAccessEventNoAuthInviteeRegisterAPI)

from app.corporate_access_resources.corporate_access_event_attendees.api \
    import (CorporateAccessEventAttendeeAPI,
            CorporateAccessEventAttendeeListAPI,
            BulkCorporateAccessEventAttendeeAPI)

from app.corporate_access_resources.corporate_access_event_participants.api \
    import (CorporateAccessEventParticipantAPI,
            CorporateAccessEventParticipantListAPI)

from app.corporate_access_resources.corporate_access_event_hosts.api import (
    CorporateAccessEventHostAPI, CorporateAccessEventHostListAPI)

from app.corporate_access_resources.corporate_access_event_inquiries.api \
    import CorporateAccessEventInquiryAPI, CorporateAccessEventInquiryListAPI

from app.corporate_access_resources.ref_event_types.api import (
    CARefEventTypeAPI, CARefEventTypeListAPI)

from app.corporate_access_resources.corporate_access_event_slots.api import (
    CorporateAccessEventSlotAPI, CorporateAccessEventSlotListAPI)

from app.corporate_access_resources.corporate_access_event_stats.api import (
    CorporateAccessEventStatsAPI, CorporateAccessEventStatsListAPI,
    CorporateAccessEventStatsOverallAPI)

from app.corporate_access_resources.corporate_access_events.api import (
    CorporateAccessEventAPI, CorporateAccessEventListAPI,
    CorporateAccessEventCancelledAPI, ReSendMailToCAEventInvitee,
    CorporateAccessEventNoAuthListAPI, CorporateAccessEventNoAuthAPI)

from app.corporate_access_resources.corporate_access_events.admin_api import (
    AdminCorporateAccessEventAPI, AdminCorporateAccessEventListAPI,
    AdminCorporateAccessEventCancelledAPI)

from app.corporate_access_resources.ref_event_sub_types.api import (
    CARefEventSubTypeAPI, CARefEventSubTypeListAPI)

from app.corporate_access_resources.corporate_access_event_collaborators.api \
    import (CorporateAccessEventCollaboratorAPI,
            CorporateAccessEventCollaboratorListAPI)

from app.corporate_access_resources.corporate_access_event_agendas.api import \
    CorporateAccessEventAgendaListAPI, CorporateAccessEventAgendaAPI

from app.corporate_access_resources.ca_open_meetings.api import \
    CAOpenMeetingAPI, CAOpenMeetingListAPI, CAOpenMeetingCancelledAPI, \
    CAOpenMeetingToCAEventConversionAPI

from app.corporate_access_resources.ca_open_meeting_invitees.api import \
    CAOpenMeetingInviteeAPI, CAOpenMeetingInviteeListAPI

from app.corporate_access_resources.ca_open_meeting_participants.api import \
    CAOpenMeetingParticipantAPI, CAOpenMeetingParticipantListAPI

from app.corporate_access_resources.ca_open_meeting_slots.api import \
    CAOpenMeetingSlotAPI, CAOpenMeetingSlotListAPI

from app.corporate_access_resources.ca_open_meeting_inquiries.api import \
    CAOpenMeetingInquiryAPI, CAOpenMeetingInquiryListAPI

corporate_access_api_bp = Blueprint('corporate_access_api', __name__,
                                    url_prefix='/api/corporate-access/v1.0')
corporate_access_api = CustomBaseApi(corporate_access_api_bp)

# corporate access event rsvp
corporate_access_api.add_resource(
    CorporateAccessEventRSVPListAPI, '/corporate-access-rsvps')
corporate_access_api.add_resource(
    CorporateAccessEventRSVPAPI, '/corporate-access-rsvps', methods=['POST'],
    endpoint='corporateaccesseventrsvppostapi')
corporate_access_api.add_resource(
    CorporateAccessEventRSVPAPI, '/corporate-access-rsvps/<int:row_id>',
    methods=['PUT', 'GET', 'DELETE'])

# corporate access event invitee
corporate_access_api.add_resource(
    CorporateAccessEventInviteeListAPI, '/corporate-access-invitee')
corporate_access_api.add_resource(
    CorporateAccessEventInviteeAPI, '/corporate-access-invitee',
    methods=['POST'], endpoint='corporateaccesseventinviteepostapi')
corporate_access_api.add_resource(
    CorporateAccessEventInviteeAPI, '/corporate-access-invitee/<int:row_id>',
    methods=['GET', 'PUT', 'DELETE'])

corporate_access_api.add_resource(
    CorporateAccessEventInviteeJoinedAPI,
    '/corporate-access-invitee-joined/<int:row_id>', methods=['PUT', 'DELETE'])
corporate_access_api.add_resource(
    CorporateAccessEventInviteeRegisterAPI,
    '/corporate-access-invitee-register', methods=['POST'])
corporate_access_api.add_resource(
    CorporateAccessEventNoAuthInviteeRegisterAPI,
    '/public-corporate-invitees/register', methods=['POST'])

# corporate access event attendees
corporate_access_api.add_resource(
    CorporateAccessEventAttendeeListAPI, '/corporate-access-event-attendees')
corporate_access_api.add_resource(
    CorporateAccessEventAttendeeAPI, '/corporate-access-event-attendees',
    methods=['POST'], endpoint='corporateaccesseventattendeepostapi')
corporate_access_api.add_resource(
    CorporateAccessEventAttendeeAPI, '/corporate-access-event-attendees/'
    '<int:row_id>', methods=['GET', 'PUT', 'DELETE'])
corporate_access_api.add_resource(
    BulkCorporateAccessEventAttendeeAPI,
    '/bulk-corporate-access-event-attendees')

# corporate access event participants
corporate_access_api.add_resource(
    CorporateAccessEventParticipantListAPI, '/corporate-access-participants')
corporate_access_api.add_resource(
    CorporateAccessEventParticipantAPI, '/corporate-access-participants',
    methods=['POST'], endpoint='corporateaccesseventparticipantpostapi')
corporate_access_api.add_resource(
    CorporateAccessEventParticipantAPI,
    '/corporate-access-participants/<int:row_id>',
    methods=['PUT', 'GET', 'DELETE'])

# corporate access event host
corporate_access_api.add_resource(
    CorporateAccessEventHostListAPI, '/corporate-access-event-hosts')
corporate_access_api.add_resource(
    CorporateAccessEventHostAPI, '/corporate-access-event-hosts',
    methods=['POST'], endpoint='corporateaccesseventhostpostapi')
corporate_access_api.add_resource(
    CorporateAccessEventHostAPI, '/corporate-access-event-hosts/<int:row_id>',
    methods=['PUT', 'GET', 'DELETE'])

# corporate access event inquiry
corporate_access_api.add_resource(
    CorporateAccessEventInquiryListAPI, '/corporate-access-inquiry')
corporate_access_api.add_resource(
    CorporateAccessEventInquiryAPI, '/corporate-access-inquiry',
    methods=['POST'], endpoint='corporateaccesseventinquirypostapi')
corporate_access_api.add_resource(
    CorporateAccessEventInquiryAPI, '/corporate-access-inquiry/<int:row_id>',
    methods=['GET', 'PUT', 'DELETE'])

# reference event types
corporate_access_api.add_resource(CARefEventTypeListAPI, '/ref-event-types')
corporate_access_api.add_resource(
    CARefEventTypeAPI, '/ref-event-types',
    methods=['POST'], endpoint='carefeventtypepostapi')
corporate_access_api.add_resource(
    CARefEventTypeAPI, '/ref-event-types/<int:row_id>',
    methods=['GET', 'PUT', 'DELETE'])

# corporate access event slot
corporate_access_api.add_resource(
    CorporateAccessEventSlotListAPI, '/corporate-access-event-slots')
corporate_access_api.add_resource(
    CorporateAccessEventSlotAPI, '/corporate-access-event-slots',
    methods=['POST'], endpoint='corporateaccesseventslotpostapi')
corporate_access_api.add_resource(
    CorporateAccessEventSlotAPI, '/corporate-access-event-slots/<int:row_id>',
    methods=['PUT', 'GET', 'DELETE'])

# corporate access event
corporate_access_api.add_resource(
    CorporateAccessEventListAPI, '/corporate-access-event')
corporate_access_api.add_resource(
    CorporateAccessEventNoAuthListAPI, '/corporate-access-event-no-auth')
corporate_access_api.add_resource(
    CorporateAccessEventAPI, '/corporate-access-event',
    methods=['POST'], endpoint='corporateaccesseventpostapi')
corporate_access_api.add_resource(
    CorporateAccessEventAPI, '/corporate-access-event/<int:row_id>',
    methods=['GET', 'PUT', 'DELETE'])
corporate_access_api.add_resource(
    CorporateAccessEventNoAuthAPI,
    '/corporate-access-event-no-auth/<int:row_id>')
corporate_access_api.add_resource(
    CorporateAccessEventCancelledAPI, '/corporate-access-event-cancel'
    '/<int:row_id>', methods=['PUT'])
corporate_access_api.add_resource(
    ReSendMailToCAEventInvitee,
    '/resend-invitee-emails/<int:row_id>', methods=['PUT'])

# admin corporate access event
corporate_access_api.add_resource(
    AdminCorporateAccessEventListAPI, '/admin-corporate-access-event')
corporate_access_api.add_resource(
    AdminCorporateAccessEventAPI, '/admin-corporate-access-event',
    methods=['POST'], endpoint='admincorporateaccesseventpostapi')
corporate_access_api.add_resource(
    AdminCorporateAccessEventAPI, '/admin-corporate-access-event/<int:row_id>',
    methods=['GET', 'PUT', 'DELETE'], endpoint='admincorporateaccesseventapi')
corporate_access_api.add_resource(
    AdminCorporateAccessEventCancelledAPI,
    '/admin-corporate-access-event-cancel/<int:row_id>', methods=['PUT'])

# reference event sub types
corporate_access_api.add_resource(
    CARefEventSubTypeListAPI, '/ref-event-sub-types')
corporate_access_api.add_resource(
    CARefEventSubTypeAPI, '/ref-event-sub-types',
    methods=['POST'], endpoint='carefeventsubtypepostapi')
corporate_access_api.add_resource(
    CARefEventSubTypeAPI, '/ref-event-sub-types/<int:row_id>',
    methods=['GET', 'PUT', 'DELETE'])

# reference event collaborators
corporate_access_api.add_resource(
    CorporateAccessEventCollaboratorListAPI,
    '/corporate-access-event-collaborators')
corporate_access_api.add_resource(
    CorporateAccessEventCollaboratorAPI,
    '/corporate-access-event-collaborators', methods=['POST'],
    endpoint='caacesseventcolloaboratorapi')
corporate_access_api.add_resource(
    CorporateAccessEventCollaboratorAPI,
    '/corporate-access-event-collaborators/<int:row_id>',
    methods=['GET', 'PUT', 'DELETE'])

# corporate access event stats
corporate_access_api.add_resource(
    CorporateAccessEventStatsListAPI, '/corporate-access-event-stats')
corporate_access_api.add_resource(
    CorporateAccessEventStatsAPI, '/corporate-access-event-stats/<int:row_id>',
    methods=['GET'])
corporate_access_api.add_resource(CorporateAccessEventStatsOverallAPI,
                                  '/corporate-access-stats-overall')

corporate_access_api.add_resource(
    CorporateAccessEventAgendaAPI,
    '/corporate-access-event-agendas/<int:row_id>')
corporate_access_api.add_resource(
    CorporateAccessEventAgendaListAPI, '/corporate-access-event-agendas')

# ca open meetings
corporate_access_api.add_resource(
    CAOpenMeetingAPI, '/ca-open-meeting', methods=['POST'],
    endpoint='caopenmeetingpostapi')
corporate_access_api.add_resource(
    CAOpenMeetingAPI, '/ca-open-meeting/<int:row_id>',
    methods=['DELETE', 'GET'])
corporate_access_api.add_resource(CAOpenMeetingListAPI, '/ca-open-meeting')
corporate_access_api.add_resource(
    CAOpenMeetingCancelledAPI, '/ca-open-meeting-cancel/<int:row_id>',
    methods=['PUT'])

# ca open meeting invitee
corporate_access_api.add_resource(
    CAOpenMeetingInviteeListAPI, '/ca-open-meeting-invitee')
corporate_access_api.add_resource(
    CAOpenMeetingInviteeAPI, '/ca-open-meeting-invitee',
    methods=['POST'], endpoint='caopenmeetinginviteepostapi')
corporate_access_api.add_resource(
    CAOpenMeetingInviteeAPI, '/ca-open-meeting-invitee/<int:row_id>',
    methods=['GET', 'PUT', 'DELETE'])

# ca open meeting participant
corporate_access_api.add_resource(
    CAOpenMeetingParticipantListAPI, '/ca-open-meeting-participant')
corporate_access_api.add_resource(
    CAOpenMeetingParticipantAPI, '/ca-open-meeting-participant',
    methods=['POST'], endpoint='caopenmeetingparticipantpostapi')
corporate_access_api.add_resource(
    CAOpenMeetingParticipantAPI, '/ca-open-meeting-participant/<int:row_id>',
    methods=['GET', 'PUT', 'DELETE'])

# ca open meeting slot
corporate_access_api.add_resource(
    CAOpenMeetingSlotListAPI, '/ca-open-meeting-slots')
corporate_access_api.add_resource(
    CAOpenMeetingSlotAPI, '/ca-open-meeting-slots/<int:row_id>',
    methods=['GET', 'DELETE'])

# ca open meeting inquiry
corporate_access_api.add_resource(
    CAOpenMeetingInquiryListAPI, '/ca-open-meeting-inquiry')
corporate_access_api.add_resource(
    CAOpenMeetingInquiryAPI, '/ca-open-meeting-inquiry',
    methods=['POST'], endpoint='caopenmeetinginquirypostapi')
corporate_access_api.add_resource(
    CAOpenMeetingInquiryAPI, '/ca-open-meeting-inquiry/<int:row_id>',
    methods=['GET', 'PUT', 'DELETE'])

corporate_access_api.add_resource(
    CAOpenMeetingToCAEventConversionAPI,
    '/ca-open-meeting-to-caevent-conversion/<int:row_id>', methods=['POST'])
