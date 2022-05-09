"""
Store some constants related to "notifications"
"""

# notification group types
NGT_CONTACT = 'contacts'  # all contact related notifications
NGT_EVENT = 'events'  # all event related notifications
NGT_CHAT = 'chat'  # all chat notifications
NGT_GENERAL = 'general'  # all other notifications
NGT_ADMIN = 'admin'  # all notification by admin
NGT_COR_ACCESS_EVENT = 'corporate_access_event'
NGT_WEBINAR = 'webinar'
NGT_WEBCAST = 'webcast'
NGT_EMEETING = 'emeeting'
NGT_CA_OPEN_MEETING = 'ca_open_meeting'
NGT_DESIGN_LAB_PROJECT = 'design_lab_project'
NGT_ANNOUNCEMENT = 'announcement'

# reminder
NG_AC_RM = 'reminder'

PROJECT_GROUP = [NGT_EMEETING,NGT_DESIGN_LAB_PROJECT]
NOTIFICATION_GROUPS = [NGT_CONTACT, NGT_EVENT, NGT_CHAT, NGT_GENERAL,
                       NGT_COR_ACCESS_EVENT, NGT_WEBINAR, NGT_WEBCAST,
                       NGT_CA_OPEN_MEETING, NGT_ADMIN, NGT_DESIGN_LAB_PROJECT,
                       NGT_EMEETING, NG_AC_RM, NGT_ANNOUNCEMENT]
NOTIFICATION_GROUPS_CHOICES = [(v, v) for v in NOTIFICATION_GROUPS]

# notification type values
# contact requests
NT_CONTACT_REQ_RECEIVED = 'c_received'
NT_CONTACT_REQ_ACCEPTED = 'c_accepted'
NT_CONTACT_REQ_REJECTED = 'c_rejected'
# follow
NT_GENERAL_FOLLOWED = 'f_followed'
# admin publish notification
NT_ADMIN_PUBLISH_NOTIFICATION = 'a_publish_notification'
# events
NT_EVENT_INVITE_INVITED = 'e_inv_invited'
NT_EVENT_INVITE_ACCEPTED = 'e_inv_accepted'
NT_EVENT_REQ_REQUESTED = 'e_requested'
NT_EVENT_REQ_ACCEPTED = 'e_req_accepted'
# chat
NT_CHAT_NEW_MESSAGE = 'c_new_message'
# corporate announcement
NT_GENERAL_CORP_ANNOUNCEMENT = 'g_corp_announced'
NT_GENERAL_SURVEY_INVITED = 'g_survey_invited'
# #TODO: future?
# NT_GENERAL_SURVEY_RESPONDED = 'g_survey_responded'
NT_GENERAL_COMMENTED = 'g_commented'
NT_GENERAL_STARRED = 'g_starred'
# corporate access event
NT_COR_EVENT_INVITED = 'cor_event_invited'
NT_COR_HOST_ADDED = 'cor_host_added'
NT_COR_PARTICIPANT_ADDED = 'cor_participant_added'
NT_COR_COLLABORATOR_ADDED = 'cor_collaborator_added'
NT_COR_RSVP_ADDED = 'cor_rsvp_added'
NT_COR_EVENT_UPDATED_INVITEE = 'cor_event_updated_invitee'
NT_COR_EVENT_UPDATED_HOST = 'cor_event_updated_host'
NT_COR_EVENT_UPDATED_RSVP = 'cor_event_updated_rsvp'
NT_COR_EVENT_UPDATED_PARTICIPANT = 'cor_event_updated_participant'
NT_COR_EVENT_UPDATED_COLLABORATOR = 'cor_event_updated_collaborator'
NT_COR_EVENT_CANCELLED = 'cor_event_cancelled'
NT_COR_EVENT_INVITED_ACCEPTED = 'cor_event_invited_accepted'
NT_COR_EVENT_INVITED_REJECTED = 'cor_event_invited_rejected'
# webinar
NT_WEBINAR_INVITED = 'webinar_invited'
NT_WEBINAR_HOST_ADDED = 'webinar_host_added'
NT_WEBINAR_PARTICIPANT_ADDED = 'webinar_participant_added'
NT_WEBINAR_RSVP_ADDED = 'webinar_rsvp_added'
NT_WEBINAR_UPDATED_INVITEE = 'webinar_updated_invitee'
NT_WEBINAR_UPDATED_HOST = 'webinar_updated_host'
NT_WEBINAR_UPDATED_RSVP = 'webinar_updated_rsvp'
NT_WEBINAR_UPDATED_PARTICIPANT = 'webinar_updated_participant'
NT_WEBINAR_CANCELLED = 'webinar_cancelled'
# webcast
NT_WEBCAST_INVITED = 'webcast_invited'
NT_WEBCAST_HOST_ADDED = 'webcast_host_added'
NT_WEBCAST_PARTICIPANT_ADDED = 'webcast_participant_added'
NT_WEBCAST_RSVP_ADDED = 'webcast_rsvp_added'
NT_WEBCAST_UPDATED_INVITEE = 'webcast_updated_invitee'
NT_WEBCAST_UPDATED_HOST = 'webcast_updated_host'
NT_WEBCAST_UPDATED_RSVP = 'webcast_updated_rsvp'
NT_WEBCAST_UPDATED_PARTICIPANT = 'webcast_updated_participant'
NT_WEBCAST_CANCELLED = 'webcast_cancelled'
# ca open meeting
NT_CAOM_SLOT_INQUIRY_CREATED = 'ca_open_meeting_slot_inquiry_created'
NT_CAOM_SLOT_INQUIRY_CONFIRMED = 'ca_open_meeting_slot_inquiry_confirmed'
NT_CAOM_SLOT_DELETED = 'ca_open_meeting_slot_deleted'
NT_CAOM_CANCELLED = 'ca_open_meeting_cancelled'
NT_DESIGNLAB_PROJECT_ASSIGNED = 'designlab_project_assigned'
NT_DESIGNLAB_PROJECT_CREATED = 'designlab_project_created'
NT_DESIGNLAB_PROJECT_STATUS_CHANGED = 'designlab_project_status_changed'
NT_DESIGNLAB_PROJECT_CANCELLED = 'designlab_project_cancelled'
NT_DESIGNLAB_ANALYST_REQUESTED = 'designlab_analyst_requested'
# emeeting
NT_EMEETING_INVITED = 'emeeting_invited'
NT_EMEETING_UPDATED_INVITEE = 'emeeting_updated_invitee'
NT_EMEETING_CANCELLED = 'emeeting_cancelled'
NT_EMEETING_RESCHUDLE = 'emeeting_reschudle'
# bse announcements
NT_BSE_CORP_ANNOUNCEMENT = 'bse_corp_announced'

# reminder
NT_AC_RM = 'actrem'

NOTIFICATION_TYPES = [NT_CONTACT_REQ_RECEIVED, NT_CONTACT_REQ_ACCEPTED,
                      NT_CONTACT_REQ_REJECTED, NT_GENERAL_FOLLOWED,
                      NT_EVENT_INVITE_INVITED, NT_EVENT_INVITE_ACCEPTED,
                      NT_EVENT_REQ_REQUESTED, NT_EVENT_REQ_ACCEPTED,
                      NT_CHAT_NEW_MESSAGE, NT_GENERAL_CORP_ANNOUNCEMENT,
                      NT_GENERAL_SURVEY_INVITED, NT_GENERAL_COMMENTED,
                      NT_GENERAL_STARRED, NT_COR_EVENT_INVITED,
                      NT_COR_HOST_ADDED, NT_COR_PARTICIPANT_ADDED,
                      NT_COR_COLLABORATOR_ADDED, NT_COR_RSVP_ADDED,
                      NT_COR_EVENT_UPDATED_INVITEE, NT_COR_EVENT_UPDATED_HOST,
                      NT_COR_EVENT_UPDATED_RSVP,
                      NT_COR_EVENT_UPDATED_PARTICIPANT,
                      NT_COR_EVENT_UPDATED_COLLABORATOR,
                      NT_COR_EVENT_INVITED_ACCEPTED,
                      NT_COR_EVENT_INVITED_REJECTED,
                      NT_COR_EVENT_CANCELLED, NT_WEBINAR_INVITED,
                      NT_WEBINAR_HOST_ADDED, NT_WEBINAR_PARTICIPANT_ADDED,
                      NT_WEBINAR_RSVP_ADDED, NT_WEBINAR_UPDATED_INVITEE,
                      NT_WEBINAR_UPDATED_HOST, NT_WEBINAR_UPDATED_RSVP,
                      NT_WEBINAR_UPDATED_PARTICIPANT, NT_WEBINAR_CANCELLED,
                      NT_WEBCAST_INVITED, NT_WEBCAST_HOST_ADDED,
                      NT_WEBCAST_PARTICIPANT_ADDED,
                      NT_WEBCAST_RSVP_ADDED, NT_WEBCAST_UPDATED_INVITEE,
                      NT_WEBCAST_UPDATED_HOST, NT_WEBCAST_UPDATED_RSVP,
                      NT_WEBCAST_UPDATED_PARTICIPANT, NT_WEBCAST_CANCELLED,
                      NT_CAOM_SLOT_INQUIRY_CREATED,
                      NT_CAOM_SLOT_INQUIRY_CONFIRMED,
                      NT_CAOM_SLOT_DELETED, NT_CAOM_CANCELLED,
                      NT_ADMIN_PUBLISH_NOTIFICATION,
                      NT_DESIGNLAB_PROJECT_ASSIGNED,
                      NT_DESIGNLAB_PROJECT_CREATED,
                      NT_DESIGNLAB_PROJECT_STATUS_CHANGED,
                      NT_DESIGNLAB_PROJECT_CANCELLED,
                      NT_DESIGNLAB_ANALYST_REQUESTED,
                      NT_EMEETING_INVITED,
                      NT_EMEETING_UPDATED_INVITEE,
                      NT_EMEETING_CANCELLED,
                      NT_AC_RM, NT_BSE_CORP_ANNOUNCEMENT,
                      NT_EMEETING_RESCHUDLE]

NOTIFICATION_TYPES_CHOICES = [(v, v) for v in NOTIFICATION_TYPES]

# notification group members
NGT_CONTACT_GROUP = [NT_CONTACT_REQ_RECEIVED, NT_CONTACT_REQ_ACCEPTED,
                     NT_CONTACT_REQ_REJECTED]
NGT_EVENT_GROUP = [NT_EVENT_INVITE_INVITED, NT_EVENT_INVITE_ACCEPTED,
                   NT_EVENT_REQ_REQUESTED, NT_EVENT_REQ_ACCEPTED]
NGT_CHAT_GROUP = [NT_CHAT_NEW_MESSAGE]
NGT_GENERAL_GROUP = [NT_GENERAL_CORP_ANNOUNCEMENT,
                     NT_GENERAL_SURVEY_INVITED, NT_GENERAL_COMMENTED,
                     NT_GENERAL_STARRED]
NGT_ADMIN_GROUP = [NT_ADMIN_PUBLISH_NOTIFICATION]
NGT_COR_ACCESS_EVENT_GROUP = [NT_COR_EVENT_INVITED, NT_COR_HOST_ADDED,
                              NT_COR_PARTICIPANT_ADDED,
                              NT_COR_COLLABORATOR_ADDED, NT_COR_RSVP_ADDED,
                              NT_COR_EVENT_UPDATED_INVITEE,
                              NT_COR_EVENT_UPDATED_HOST,
                              NT_COR_EVENT_UPDATED_RSVP,
                              NT_COR_EVENT_UPDATED_PARTICIPANT,
                              NT_COR_EVENT_UPDATED_COLLABORATOR,
                              NT_COR_EVENT_CANCELLED]
NGT_WEBINAR_GROUP = [NT_WEBINAR_INVITED, NT_WEBINAR_HOST_ADDED,
                     NT_WEBINAR_PARTICIPANT_ADDED, NT_WEBINAR_RSVP_ADDED,
                     NT_WEBINAR_UPDATED_INVITEE, NT_WEBINAR_UPDATED_HOST,
                     NT_WEBINAR_UPDATED_RSVP, NT_WEBINAR_UPDATED_PARTICIPANT,
                     NT_WEBINAR_CANCELLED]
NGT_WEBCAST_GROUP = [NT_WEBCAST_INVITED, NT_WEBCAST_HOST_ADDED,
                     NT_WEBCAST_PARTICIPANT_ADDED, NT_WEBCAST_RSVP_ADDED,
                     NT_WEBCAST_UPDATED_INVITEE, NT_WEBCAST_UPDATED_HOST,
                     NT_WEBCAST_UPDATED_RSVP, NT_WEBCAST_UPDATED_PARTICIPANT,
                     NT_WEBCAST_CANCELLED]
NGT_CA_OPEN_MEETING_GROUP = [NT_CAOM_SLOT_INQUIRY_CREATED,
                             NT_CAOM_SLOT_INQUIRY_CONFIRMED,
                             NT_CAOM_SLOT_DELETED, NT_CAOM_CANCELLED]
NGT_DESIGN_LAB_GROUP = [NT_DESIGNLAB_PROJECT_ASSIGNED,
                        NT_DESIGNLAB_PROJECT_CREATED,
                        NT_DESIGNLAB_PROJECT_STATUS_CHANGED,
                        NT_DESIGNLAB_PROJECT_CANCELLED]

# notification standard messages
NOTIFICATION_MESSAGES = {
    # contact group
    NT_CONTACT_REQ_RECEIVED: '%(first_name)s %(last_name)s sent you a contact '
                             'request.',
    NT_CONTACT_REQ_ACCEPTED: 'You are now connected with %(first_name)s '
                             '%(last_name)s',
    NT_CONTACT_REQ_REJECTED: '%(name)s has rejected your contact request',
    # general followed
    NT_GENERAL_FOLLOWED: '%(first_name)s %(last_name)s has followed your '
                         'company',
    # event group
    NT_EVENT_INVITE_INVITED: 'You have been invited to attend %(event_name)s',
    NT_EVENT_INVITE_ACCEPTED: '%(name)s has accepted your invite to your event'
    '%(event_name)s',
    NT_EVENT_REQ_REQUESTED: '%(name)s has requested to join your event '
    '%(event_name)s',
    NT_EVENT_REQ_ACCEPTED: 'Your request to join the event %(name)s has been '
    'accepted',
    # chat group
    NT_CHAT_NEW_MESSAGE: '%(sender)s sent you a message',
    # general group
    NT_GENERAL_CORP_ANNOUNCEMENT: '%(company)s has made an announcement '
    '%(announcement_title)s',
    NT_GENERAL_SURVEY_INVITED: '%(company)s has invited you to a survey',
    NT_GENERAL_COMMENTED: '%(commenter)s has commented on your post '
    '%(post_title)s',
    NT_GENERAL_STARRED: '%(starrer)s has starred your post %(post_title)s',
    NT_WEBCAST_INVITED: '%(first_name)s %(last_name)s has invited you for '
                        'a webcast %(event_name)s.',
    NT_WEBCAST_HOST_ADDED: '%(first_name)s %(last_name)s has invited you '
                           'for host a webcast %(event_name)s.',
    NT_WEBCAST_PARTICIPANT_ADDED: '%(first_name)s %(last_name)s has invited '
                                  'you for participate a webcast %(event_name)s.',
    NT_WEBCAST_RSVP_ADDED: 'has invited you for become rsvp of a webcast '
                           '%(event_name)s.',
    NT_WEBCAST_CANCELLED: '%(event_name)s has been cancelled',
    NT_EMEETING_INVITED: '%(first_name)s %(last_name)s has invited you for '
                        'a emeeting %(event_name)s.',
    NT_EMEETING_CANCELLED: '%(event_name)s has been cancelled',
    NT_AC_RM: '%(type)s: %(subject)s coming up on %(due_time)s',
    NT_WEBINAR_INVITED: '%(first_name)s %(last_name)s has invited you for '
                        'a webinar %(event_name)s.',
    NT_WEBINAR_HOST_ADDED: '%(first_name)s %(last_name)s has invited you '
                           'for host a webinar %(event_name)s.',
    NT_WEBINAR_PARTICIPANT_ADDED: '%(first_name)s %(last_name)s has invited '
                                  'you for participate a webinar %(event_name)s.',
    NT_WEBINAR_RSVP_ADDED: 'has invited you for become rsvp of a webinar '
                           '%(event_name)s.',
    NT_WEBINAR_CANCELLED: '%(event_name)s has been cancelled',
    NT_COR_EVENT_INVITED: '%(first_name)s %(last_name)s has invited you for '
                          'an event %(event_name)s.',
    NT_COR_COLLABORATOR_ADDED: 'has invited you for become collaborator of an '
                               'event %(event_name)s.',
    NT_COR_PARTICIPANT_ADDED: '%(first_name)s %(last_name)s has invited you '
                              ' you for participate an event %(event_name)s.',
    NT_COR_HOST_ADDED: '%(first_name)s %(last_name)s has invited you '
                       'for host an event %(event_name)s.',
    NT_COR_RSVP_ADDED: 'has invited you for become rsvp of an '
                       'event %(event_name)s.',
    NT_COR_EVENT_CANCELLED: '%(event_name)s has been cancelled',
    NT_COR_EVENT_INVITED_REJECTED: '%(first_name)s %(last_name)s has rejected '
                                   'your event request for %(event_name)s',
    NT_COR_EVENT_INVITED_ACCEPTED: '%(first_name)s %(last_name)s has accepted '
                                   'your event request for %(event_name)s',
    NT_CAOM_SLOT_INQUIRY_CREATED: '%(first_name)s %(last_name)s has inquired '
                                  'for %(slot_name)s in %(event_name)s',

    NT_CAOM_SLOT_INQUIRY_CONFIRMED: 'Your %(slot_name)s request for '
                                    '%(event_name)s has confirmed',
    NT_CAOM_SLOT_DELETED: 'Your %(slot_name)s request for %(event_name)s '
                          'has been cancelled',

    NT_CAOM_CANCELLED: '%(event_name)s has been cancelled',
    NT_DESIGNLAB_PROJECT_ASSIGNED: "You have a new design lab project assigned",
    # BSE feed
    NT_BSE_CORP_ANNOUNCEMENT: '%(company)s has made an announcement '
        '%(announcement_title)s'
}

# CHOICE for main filter

GENERAL = 'general'
DESIGNLAB = 'designlab'
TYPE_LISTS = [GENERAL,DESIGNLAB]
