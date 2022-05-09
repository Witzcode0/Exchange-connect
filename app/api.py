"""
Social Network + user resources apis
"""

from flask import Blueprint

from app.common.helpers import add_response_headers

from app.auth.api import (
    LoginAPI, ForgotPasswordAPI, SwitchAccountUserLoginAPI, DesignLabLoginAPI,
    DesignLabForgotPasswordAPI)
from app.auth.admin_api import AdminLoginAsAPI, AdminLoginAPI
from app.auth.api import TokenVerificationAPI
from app.resources.audio_transcribe.api import AudioTranscribeListAPI, AudioTranscribeAPI
from app.resources.result_tracker.api import ResultTrackerGroupListAPI, ResultTrackerGroupAPI, ResultTrackerGroupBulkAPI
from app.resources.result_tracker_companies.api import ResultTrackerGroupCompaniesAPI, \
    ResultTrackerGroupCompaniesListAPI, ResultTrackerGroupCompaniesBulkEditAPI, \
    ResultTrackerGroupCompaniesBulkDeleteAPI

from app.resources.users.api import (
    UserAPI, UserListAPI, ChangePasswordAPI, FirstTimeChangePasswordAPI,
    UserOrderAPI, AdminUserOrderAPI, DesignLabChangePasswordAPI)
from app.resources.guest_user.api import GuestUserAPI
from app.resources.registration_requests.api import (
    RegistrationRequestPostAPI, RegistrationRequestEmailVerifyAPI,
    RegistrationRequestAPI, RegistrationRequestList,
    RegistrationRequestAddUserAPI, DesignLabRegistrationRequestPostAPI,
    RegistrationRequestReSendEmailVerifyAPI)
from app.resources.user_profiles.api import (
    UserProfileAPI, UserProfileListAPI, DesignLabUserProfileAPI)
from app.resources.user_settings.api import UserSettingsAPI

from app.resources.user_dashboard.api import (
    UserDashboardStatsListAPI, UserEventMonthWiseStatsListAPI,
    UserMonthWiseEventTypeStatsListAPI)

from app.resources.events.api import EventAPI, EventsListAPI

from app.resources.event_types.api import EventTypeAPI, EventTypeListAPI

from app.resources.event_bookmarks.api import (
    EventBookmarkAPI, EventBookmarkListAPI)

from app.resources.events.admin_api import AdminEventAPI, AdminEventsListAPI

from app.resources.event_invites.api import EventInviteAPI, EventInvitesListAPI

from app.resources.event_requests.api import (
    EventRequestAPI, EventRequestsListAPI, OpenEventJoinAPI,
    BulkEventInviteStatusChangeAPI)

from app.resources.event_file_library.api import (
    EventLibraryFileAPI, EventLibraryFileListAPI)

from app.resources.accounts.admin_api import (
    AccountAPI, AccountList, UpdateSmeAccounts, AccountBulkCreateApi)
from app.resources.account_stats.api import AccountStatsList
from app.resources.account_profiles.api import (
    AccountProfileAPI, AccountProfileListAPI, AccountProfileTeamListAPI,
    AccountProfileNoAuthListAPI, AccountProfileNoAuthAPI,
    AccountProfileTeamNoAuthListAPI)
from app.resources.account_settings.api import (
    AccountSettingsAPI, VerifySenderEmailAPI, RemoveVerifySenderEmailAPI)
from app.resources.account_managers.api import (
    AccountManagerAPI, AccountManagerList)

from app.resources.roles.api import RoleAPI, RoleList

from app.resources.contact_requests.api import (
    ContactRequestAPI, ContactRequestListAPI)

from app.resources.contacts.api import (
    ContactAPI, ContactListAPI, ContactAddByQRCodeAPI)
from app.resources.contacts.admin_api import AdminContactListAPI

from app.resources.user_profiles.chat_api import UserProfileChatAPI

from app.resources.file_archives.api import (
    ArchiveFileAPI, ArchiveFileListAPI, ArchiveFileLibraryListAPI)

from app.resources.follows.api import (
    CFollowAPI, CFollowListAPI, CFollowAnalysisAPI)

from app.resources.posts.api import PostAPI, PostListAPI

from app.resources.posts.admin_api import AdminPostAPI, AdminPostListAPI

from app.resources.post_comments.api import PostCommentAPI, PostCommentListAPI

from app.resources.post_comments.admin_api import AdminPostCommentAPI

from app.resources.post_stars.api import PostStarAPI, PostStarListAPI

from app.resources.post_file_library.api import (
    PostLibraryFileAPI, PostLibraryFileListAPI)

from app.resources.news.api import (
    NewsSourceAPI, NewsSourceListAPI, NewsItemListAPI, NewsItemNoAuthListAPI, 
    TopNewsAPI, TopNewsListAPI)

from app.resources.news_archive.api import (
    NewsItemArchiveAPI, NewsItemArchiveListAPI)

from app.survey_resources.survey_responses.api import (
    SurveyResponseAPI, SurveyResponseDeleteAPI, SurveyResponseListAPI)

from app.resources.companies.api import CompanyAPI, CompanyListAPI
from app.resources.sectors.api import SectorAPI, SectorListAPI
from app.resources.industries.api import IndustryAPI, IndustryListAPI
from app.resources.designations.api import DesignationAPI, DesignationListAPI

from app.resources.feeds.api import FeedItemAPI, FeedItemListAPI

from app.survey_resources.surveys.api import (
    SurveyAPI, SurveyListAPI, SurveyGetAPI, ReSendMailToSurveyInvitee)
from app.survey_resources.survey_stats.api import SurveyOverallStatsAPI

from app.resources.shares.api import ShareAPI

from app.resources.notifications.api import (
    NotificationAPI, NotificationListAPI, AllNotificationsAsRead)

from app.resources.management_profiles.api import (
    ManagementProfileAPI, ManagementProfileListAPI,
    ManagementProfileOrderAPI)
from app.resources.management_profiles.admin_api import (
    AdminManagementProfileAPI, AdminManagementProfileOrderAPI)

from app.resources.ref_time_zones.api import RefTimeZoneListApi
from app.resources.countries.api import CountryAPI, CountryListAPI
from app.resources.states.api import StateAPI, StateListAPI
from app.resources.cities.api import CityAPI, CityListAPI

from app.resources.company_page_file_library.api import (
    CompanyPageLibraryFileAPI, CompanyPageLibraryFileListAPI)
from app.resources.company_pages.api import CompanyPageAPI, CompanyPageListAPI

from app.resources.activities.api import GlobalActivityGetListApi

from app.resources.event_calendars.api import EventCalendarListAPI

from app.resources.corporate_announcements.api import (
    CorporateAnnouncementAPI, CorporateAnnouncementListAPI,
    CorporateAnnouncementNoAuthAPI, CorporateAnnouncementNoAuthListAPI)
from app.resources.corporate_announcements_category.admin_api import ( AdminCorporationCategoryAPI, AdminCorporateAnnouncementCategoryListAPI)
from app.resources.corporate_announcements.admin_api import (
    AdminCorporateAnnouncementAPI,AdminCorporateBulkAnnouncementAPI ,AdminCorporateAnnouncementListAPI,
    CorporateAnnouncementXMLAPI)

from app.resources.admin_dashboard.api import AdminDashboardStatsListAPI

from app.resources.inquiries.api import (
    InquiryContactUsPostAPI, InquiryAPI, InquiryListAPI, InquiryPlanPostAPI)

from app.resources.admin_publish_notifications.api import (
    AdminPublishNotificationAPI, AdminPublishNotificationListAPI)

from app.resources.unsubscriptions.api import (UnsubscriptionAPI,
    UserUnsubscriptionAPI, UnsubscribeReasonListAPI)
from app.resources.unsubscriptions.admin_api import (UnsubscriptionListAPI,
    AdminUnsubscriptionAPI, UnsubscribeReasonAPI)

from app import CustomBaseApi

from app.frontend_tests_api import FrontendEmailTestsAPI

from app.resources.menu.admin_api import MenuAPI, MenuListAPI, BulkMenuUpdate
from app.resources.permissions.admin_api import (
    PermissionAPI, PermissionListAPI)
from app.resources.user_profiles.api import UserRoleAPI
from app.resources.email_credentials.api import EmailCredentialAPI
from app.resources.scheduled_reports.api import (
    ScheduledReportAPI, ScheduledReportListAPI, ScheduledReportLogApi)
from app.resources.scheduled_reports.admin_api import (
    AdminScheduledReportListAPI, AdminScheduledReportUserwiseAPI,
    AdminScheduledReportLogListAPI)
from app.global_search.api import SearchAPI
from app.resources.twitter_feeds.api import (
    TwitterFeedListAPI, TwitterSourceFeedAPI)

from app.domain_resources.domains.admin_api import DomainAPI, DomainListAPI
from app.domain_resources.domain_config.admin_api import (
    DomainConfigAPI, DomainConfigListAPI)
from app.webinar_resources.webinars.api import PublishRecordingAPI

from app.resources.login_logs.admin_api import LoginLogListAPI
from app.resources.user_activity_logs.admin_api import (
    UserActivityLogListAPI, UserActivityLogAPI, ActionVisitCountAPI,
    VisitsActionsOverTimeAPI, UserActivityLogRecordListAPI)

from app.resources.bse.api import BSEFeedListAPI,BSEFeedAPI, BSEFeedStatsAPI
from app.toolkit_resources.project_history.admin_api import (
    ProjectHistoryAdminAnalystAPI, ProjectHistoryAdminAnalystListAPI)

from app.market_resources.market_comment.api import (
    MarketCommentAPI, MarketCommentListAPI)

from app.market_resources.market_performance.api import (
    MarketPerformanceAPI, MarketPerformanceListAPI)

from app.news_letter.distribution_list.api import (DistributionListAPI,
    DistributionListofListAPI, DistributionListXLSAPI, 
    DistributionBulkAPI, DistributionBulkDeletAPI,
    DistributionListFrontEndAPI)

from app.news_letter.email_logs.api import (
    EmailLogListAPI,
    EmailRecordcount)
from app.resources.email_statics.api import EmailStatic, EmailStaticListAPI

from app.resources.ir_module.api import (
    IrModuleAPI,
    IrModuleListAPI,
    IrModuleHeadingAPI,
    IrModuleHeadingListAPI)
from app.resources.ir_module.admin_api import (
    IrModuleAdminListAPI)

# Activity log
from app.activity.activities.api import ActivityAPI, ActivityList

from app.resources.goaltrackers.api import GoalTrackerAPI, GoalTrackerList

from app.resources.activity_type.api import ActivityTypeListAPI, ActivityTypeAPI
from app.activity.activities_representative.api import RepresentativeAPI
from app.activity.activities_institution.api import ActivityIntituteFactSetList
from app.resources.cron_job.api import (
    CronJobAPI,
    CronListAPI,
    CronActivity)

from app.resources.personalised_video.api import PersonalisedVideoAPI
from app.resources.personalised_video.admin_api import AdminPersonalisedVideoAPI, PersonalisedVideoListAPI
from app.resources.personalised_video_logs.api import PersonalisedVideoLogListAPI

from app.health_check.api import HealthCheckAPI
from app.resources.corporate_announcements_category.api import CorporateAnnouncementCategoryListAPI

from app.resources.audio_transcribe.api import AudioTranscribeListAPI, AudioTranscribeAPI

from app.resources.descriptor.admin_api import AdminBSEDescriptorAPI, AdminBSEDescriptorListAPI
# only for tests
fetest_api_bp = Blueprint('fetestapi', __name__, url_prefix='/api/fetest/v1.0')
fetest_api = CustomBaseApi(fetest_api_bp)
fetest_api.add_resource(FrontendEmailTestsAPI, '/email-tests')


api_bp = Blueprint('api', __name__, url_prefix='/api/v1.0')
api_bp.after_app_request(add_response_headers)
api = CustomBaseApi(api_bp)

# registration requests and related
api.add_resource(RegistrationRequestList, '/registrations')
api.add_resource(RegistrationRequestPostAPI, '/registrations',
                 methods=['POST'])
api.add_resource(
    DesignLabRegistrationRequestPostAPI, '/design-lab-registrations',
    methods=['POST'])
api.add_resource(RegistrationRequestAPI, '/registrations/<int:row_id>')
api.add_resource(RegistrationRequestEmailVerifyAPI,
                 '/registrations/verify/<string:token>')
api.add_resource(RegistrationRequestAddUserAPI,
                 '/registrations/add-user/<int:row_id>')
api.add_resource(RegistrationRequestReSendEmailVerifyAPI,
                 '/registrations/resend-email/<int:row_id>')

api.add_resource(EventAPI, '/events', methods=['POST'],
                 endpoint='eventpostapi')
api.add_resource(EventAPI, '/events/<int:row_id>',
                 methods=['GET', 'PUT', 'DELETE'])
api.add_resource(EventsListAPI, '/events')

# event type
api.add_resource(EventTypeAPI, '/events/event-types', methods=['POST'],
                 endpoint='eventtypepostapi')
api.add_resource(EventTypeAPI, '/events/event-types/<int:row_id>',
                 methods=['GET', 'PUT', 'DELETE'])
api.add_resource(EventTypeListAPI, '/events/event-types')

# event bookmark
api.add_resource(EventBookmarkAPI, '/event-bookmarks', methods=['POST'],
                 endpoint='eventbookmarkpostapi')
api.add_resource(EventBookmarkAPI, '/event-bookmarks/<int:row_id>',
                 methods=['GET', 'DELETE'])
api.add_resource(EventBookmarkListAPI, '/event-bookmarks')

# # admin event
api.add_resource(AdminEventAPI, '/admin-events', methods=['POST'],
                 endpoint='admineventpostapi')
api.add_resource(AdminEventAPI, '/admin-events/<int:row_id>',
                 methods=['GET', 'PUT', 'DELETE'])
api.add_resource(AdminEventsListAPI, '/admin-events')
api.add_resource(AdminDashboardStatsListAPI, '/admin-dashboard')

api.add_resource(EventInviteAPI, '/event-invites', methods=['POST'],
                 endpoint='eventinvitepostapi')
api.add_resource(EventInviteAPI, '/event-invites/<int:row_id>',
                 methods=['GET', 'PUT', 'DELETE'])
api.add_resource(EventInvitesListAPI, '/event-invites')

api.add_resource(OpenEventJoinAPI, '/open-event-joins', methods=['POST'],
                 endpoint='openeventjoinpostapi')

api.add_resource(EventRequestAPI, '/event-requests', methods=['POST'],
                 endpoint='eventrequestspostapi')
api.add_resource(EventRequestAPI, '/event-requests/<int:row_id>',
                 methods=['GET', 'PUT', 'DELETE'])
api.add_resource(EventRequestsListAPI, '/event-requests')

# Event file library
api.add_resource(EventLibraryFileAPI, '/event-files', methods=['POST'],
                 endpoint='eventlibraryfilepostapi')
api.add_resource(EventLibraryFileAPI, '/event-files/<int:row_id>',
                 methods=['PUT', 'DELETE', 'GET'])
api.add_resource(EventLibraryFileListAPI, '/event-files')

# Company page file library
api.add_resource(CompanyPageLibraryFileAPI, '/company-page-files',
                 methods=['POST'], endpoint='companypagelibraryfilepostapi')
api.add_resource(CompanyPageLibraryFileAPI, '/company-page-files/<int:row_id>',
                 methods=['PUT', 'DELETE', 'GET'])
api.add_resource(CompanyPageLibraryFileListAPI, '/company-page-files')

api.add_resource(BulkEventInviteStatusChangeAPI,
                 '/events/invite-change-status/<int:event_id>')

api.add_resource(UserListAPI, '/users')
api.add_resource(UserAPI, '/users', methods=['POST'], endpoint='userpostapi')
api.add_resource(UserAPI, '/users/<int:row_id>',
                 methods=['PUT', 'GET', 'DELETE'])
api.add_resource(UserOrderAPI, '/users-order', methods=['PUT'])
api.add_resource(AdminUserOrderAPI, '/admin-users-order', methods=['PUT'])
api.add_resource(GuestUserAPI, '/guest-users', methods=['POST'])

# login
api.add_resource(LoginAPI, '/auth/login')
api.add_resource(DesignLabLoginAPI, '/auth/design-lab-login')
# admin login apis
api.add_resource(AdminLoginAPI, '/auth/admin-login')
# Admin login as a normal user
api.add_resource(AdminLoginAsAPI, '/auth/admin-login-as')
# login for switch account
api.add_resource(SwitchAccountUserLoginAPI, '/auth/switch-account')
# forgot password
api.add_resource(ForgotPasswordAPI, '/auth/forgotpass', methods=['POST'])
api.add_resource(ForgotPasswordAPI, '/auth/forgotpass/<string:token>',
                 methods=['PUT'], endpoint='forgotpasswordresetapi')
#designlab forgot password
api.add_resource(
    DesignLabForgotPasswordAPI, '/auth/design-lab-forgotpass', methods=['POST'])
api.add_resource(
    DesignLabForgotPasswordAPI, '/auth/design-lab-forgotpass/<string:token>',
    methods=['PUT'], endpoint='designlabforgotpasswordresetapi')

# change password by user
api.add_resource(ChangePasswordAPI, '/users/edit/password')
api.add_resource(FirstTimeChangePasswordAPI, '/users/edit/first-password')

# change password by user
api.add_resource(DesignLabChangePasswordAPI, '/designlab-users/edit/password')

api.add_resource(AccountList, '/accounts')
api.add_resource(AccountAPI, '/accounts', methods=['POST'],
                 endpoint='accountpostapi')
api.add_resource(AccountBulkCreateApi, '/accounts-bulk-upload',
                 methods=['POST'],)
api.add_resource(AccountAPI, '/accounts/<int:row_id>',
                 methods=['PUT', 'GET', 'DELETE'])
api.add_resource(AccountStatsList, '/account-stats')

api.add_resource(AccountManagerAPI, '/account-managers', methods=['POST'],
                 endpoint='accountmanagerpostapi')
api.add_resource(AccountManagerAPI, '/account-managers/<int:row_id>',
                 methods=['DELETE', 'GET'])
api.add_resource(AccountManagerList, '/account-managers')
api.add_resource(UpdateSmeAccounts, '/update-sme-accounts', methods=['PUT'])

api.add_resource(RoleList, '/roles')
api.add_resource(RoleAPI, '/roles', methods=['POST'],
                 endpoint='rolepostapi')
api.add_resource(RoleAPI, '/roles/<int:row_id>',
                 methods=['GET', 'PUT', 'DELETE'])

# contact requests
api.add_resource(ContactRequestListAPI, '/contact-requests')
api.add_resource(ContactRequestAPI, '/contact-requests', methods=['POST'],
                 endpoint='contactrequestpostapi')
api.add_resource(ContactRequestAPI, '/contact-requests/<int:row_id>',
                 methods=['PUT', 'GET', 'DELETE'])
# contacts
api.add_resource(ContactListAPI, '/contacts')
api.add_resource(ContactAPI, '/contacts/<int:row_id>', methods=['DELETE'])
api.add_resource(ContactAddByQRCodeAPI, '/contacts/qr-contact-requests')

# Admin contact
api.add_resource(AdminContactListAPI, '/admin-contacts')

# user profiles
# update profile by current user
api.add_resource(UserProfileAPI, '/user-profiles', methods=['PUT'],
                 endpoint='userprofileputapi')
# fetch any profile by user_id
api.add_resource(UserProfileAPI, '/user-profiles/<int:user_id>',
                 methods=['GET'])
#update design lab profile by current user
api.add_resource(DesignLabUserProfileAPI, '/designlab-user-profiles',
                 methods=['PUT'], endpoint='designlabuserprofileputapi')
# fetch any profile by user_id
api.add_resource(
    DesignLabUserProfileAPI, '/designlab-user-profiles/<int:user_id>',
    methods=['GET'])
# fetch a list of profiles by some arguments
api.add_resource(UserProfileListAPI, '/user-profiles')

api.add_resource(UserProfileChatAPI, '/user-profiles-chat')

# user settings
# update settings by current user
api.add_resource(UserSettingsAPI, '/user-settings', methods=['PUT'],
                 endpoint='usersettingsputapi')
api.add_resource(UserSettingsAPI, '/user-settings', methods=['GET'])

# account profiles
# update profile by current account
# api.add_resource(AccountProfileAPI, '/account-profiles', methods=['PUT'],
#                  endpoint='accountprofileputapi')
# fetch any profile by account_id
api.add_resource(AccountProfileAPI, '/account-profiles/<int:account_id>',
                 methods=['GET', 'PUT'])
api.add_resource(AccountProfileNoAuthAPI,
                 '/account-profiles-no-auth/<int:account_id>')
api.add_resource(AccountProfileListAPI, '/account-profiles')
api.add_resource(AccountProfileNoAuthListAPI, '/account-profiles-no-auth')
api.add_resource(AccountProfileTeamListAPI,
                 '/account-profiles/teams', methods=['GET'])
api.add_resource(AccountProfileTeamNoAuthListAPI,
                 '/account-profiles/teams-no-auth')

# account settings
# update settings by current user->account
api.add_resource(AccountSettingsAPI, '/account-settings', methods=['PUT'],
                 endpoint='accountsettingsputapi')
api.add_resource(AccountSettingsAPI, '/account-settings', methods=['GET'])
api.add_resource(VerifySenderEmailAPI, '/account-settings/verify',
                 methods=['PUT'])
api.add_resource(RemoveVerifySenderEmailAPI,
                 '/account-settings/remove-verified-email', methods=['PUT'])

# Archive file
api.add_resource(ArchiveFileListAPI, '/archive-files')
api.add_resource(ArchiveFileLibraryListAPI, '/archive-files-library')
api.add_resource(ArchiveFileAPI, '/archive-files', methods=['POST'],
                 endpoint='archivefilepostapi')
api.add_resource(ArchiveFileAPI, '/archive-files/<int:row_id>',
                 methods=['PUT', 'DELETE', 'GET'])

# Company Follow
api.add_resource(CFollowAPI, '/cfollows', methods=['POST'],
                 endpoint='cfollowpostapi')
api.add_resource(CFollowAPI, '/cfollows/<int:row_id>',
                 methods=['DELETE'])
api.add_resource(CFollowListAPI, '/cfollows')
api.add_resource(CFollowAnalysisAPI, '/cfollows/analysis')

# Post
api.add_resource(PostAPI, '/posts', methods=['POST'], endpoint='postpostapi')
api.add_resource(PostAPI, '/posts/<int:row_id>',
                 methods=['DELETE', 'GET', 'PUT'])
api.add_resource(PostListAPI, '/posts')

# Admin post
api.add_resource(AdminPostAPI, '/admin-posts/<int:row_id>',
                 methods=['GET', 'DELETE'])
api.add_resource(AdminPostListAPI, '/admin-posts')


# Post share
api.add_resource(ShareAPI, '/post-shares', methods=['POST'],
                 endpoint='shareapi')

# Post Comment
api.add_resource(PostCommentAPI, '/post-comments', methods=['POST'],
                 endpoint='postcommentpostapi')
api.add_resource(PostCommentAPI, '/post-comments/<int:row_id>',
                 methods=['PUT', 'DELETE', 'GET'])
api.add_resource(PostCommentListAPI, '/post-comments')

# Admin post comment
api.add_resource(AdminPostCommentAPI, '/admin-post-comment/<int:row_id>',
                 methods=['DELETE'])

# Post star
api.add_resource(PostStarAPI, '/post-stars', methods=['POST'],
                 endpoint='poststarpostapi')
api.add_resource(PostStarAPI, '/post-stars/<int:row_id>',
                 methods=['GET', 'PUT', 'DELETE'])
api.add_resource(PostStarListAPI, '/post-stars')

# Post file library
api.add_resource(PostLibraryFileAPI, '/post-files', methods=['POST'],
                 endpoint='postlibraryfilepostapi')
api.add_resource(PostLibraryFileAPI, '/post-files/<int:row_id>',
                 methods=['PUT', 'DELETE', 'GET'])
api.add_resource(PostLibraryFileListAPI, '/post-files')

# newsfeed apis
api.add_resource(TopNewsAPI,'/top-news', methods=['POST'],
                 endpoint="topnewspostapi")
api.add_resource(TopNewsAPI,'/top-news/<int:row_id>',
                 methods=['PUT','DELETE','GET'])
api.add_resource(TopNewsListAPI,'/top-news', methods=['GET'])
api.add_resource(NewsItemListAPI, '/news',methods=['GET'])
api.add_resource(NewsItemNoAuthListAPI, '/news-no-auth')
api.add_resource(NewsSourceListAPI, '/news-sources')
api.add_resource(NewsSourceAPI, '/news-sources', methods=['POST'],
                 endpoint='newssourcespostapi')
api.add_resource(NewsSourceAPI, '/news-sources/<int:row_id>',
                 methods=['PUT', 'DELETE', 'GET'])

# newsfeed archive
api.add_resource(NewsItemArchiveListAPI, '/news-archive')
api.add_resource(NewsItemArchiveAPI, '/news-archive/<int:news_item_id>',
                 methods=['POST'], endpoint='newsitemarchivepostapi')
api.add_resource(NewsItemArchiveAPI, '/news-archive/<int:row_id>',
                 methods=['DELETE', 'GET'])

# Survey response
api.add_resource(SurveyResponseListAPI, '/survey-responses')
api.add_resource(SurveyResponseAPI, '/survey-responses/<int:row_id>',
                 methods=['PUT', 'GET'])
api.add_resource(SurveyResponseDeleteAPI, '/survey-responses/<int:row_id>',
                 methods=['DELETE'])

# sectors apis
api.add_resource(SectorAPI, '/sectors', methods=['POST'],
                 endpoint='sectorpostapi')
api.add_resource(SectorAPI, '/sectors/<int:row_id>',
                 methods=['GET', 'PUT', 'DELETE'])
api.add_resource(SectorListAPI, '/sectors')

# feed api
api.add_resource(FeedItemAPI, '/feeds/<int:row_id>',
                 methods=['GET'])
api.add_resource(FeedItemListAPI, '/feeds')

# surveys api
api.add_resource(SurveyAPI, '/surveys', methods=['POST'],
                 endpoint='surveypostapi')
api.add_resource(SurveyAPI, '/surveys/<int:row_id>',
                 methods=['DELETE', 'GET', 'PUT'])
api.add_resource(SurveyListAPI, '/surveys')
api.add_resource(SurveyOverallStatsAPI, '/survey-overall-stats',
                 methods=["GET"])
api.add_resource(SurveyGetAPI, '/surveys-get/<int:row_id>',
                 methods=['GET'])
#survey resend mail to invitees
api.add_resource(ReSendMailToSurveyInvitee,
                 '/resend-survey-invitee-emails/<int:row_id>',
                 methods=['PUT'])

# industries api
api.add_resource(IndustryAPI, '/industries', methods=['POST'],
                 endpoint='industrypostapi')
api.add_resource(IndustryAPI, '/industries/<int:row_id>',
                 methods=['DELETE', 'GET', 'PUT'])
api.add_resource(IndustryListAPI, '/industries')

# Designation apis
api.add_resource(DesignationListAPI, '/designations')
api.add_resource(DesignationAPI, '/designations',
                 methods=['POST'], endpoint='designationpostapi')
api.add_resource(DesignationAPI, '/designations/<int:row_id>',
                 methods=['PUT', 'GET', 'DELETE'])

# Notification apis
api.add_resource(NotificationAPI, '/notifications/<int:row_id>')
api.add_resource(NotificationListAPI, '/notifications')
api.add_resource(AllNotificationsAsRead, '/notifications-mark-all-read',
                 methods= ['POST'])

# Company apis
api.add_resource(CompanyListAPI, '/companies')
api.add_resource(CompanyAPI, '/companies',
                 methods=['POST'], endpoint='companypostapi')
api.add_resource(CompanyAPI, '/companies/<int:row_id>',
                 methods=['PUT', 'GET', 'DELETE'])

# ManagementProfile apis
api.add_resource(ManagementProfileListAPI, '/management-profiles')
api.add_resource(ManagementProfileAPI, '/management-profiles',
                 methods=['POST'], endpoint='managementprofilepostapi')
api.add_resource(ManagementProfileAPI, '/management-profiles/<int:row_id>',
                 methods=['PUT', 'GET', 'DELETE'])
api.add_resource(ManagementProfileOrderAPI, '/management-profiles-order',
                 methods=['PUT'])

# Admin management apis
api.add_resource(AdminManagementProfileAPI, '/admin-management-profiles',
                 methods=['POST'], endpoint='adminmanagementprofilepostapi')
api.add_resource(AdminManagementProfileAPI,
                 '/admin-management-profiles/<int:row_id>',
                 methods=['PUT', 'DELETE'])
api.add_resource(AdminManagementProfileOrderAPI,
                 '/admin-management-profiles-order', methods=['PUT'])

# Timezone api
api.add_resource(RefTimeZoneListApi, '/time-zones')

# Country apis
api.add_resource(CountryListAPI, '/countries')
api.add_resource(CountryAPI, '/countries',
                 methods=['POST'], endpoint='countrypostapi')
api.add_resource(CountryAPI, '/countries/<int:row_id>',
                 methods=['PUT', 'GET', 'DELETE'])

# State apis
api.add_resource(StateListAPI, '/states')
api.add_resource(StateAPI, '/states',
                 methods=['POST'], endpoint='statepostapi')
api.add_resource(StateAPI, '/states/<int:row_id>',
                 methods=['PUT', 'GET', 'DELETE'])

# City apis
api.add_resource(CityListAPI, '/cities')
api.add_resource(CityAPI, '/cities',
                 methods=['POST'], endpoint='citypostapi')
api.add_resource(CityAPI, '/cities/<int:row_id>',
                 methods=['PUT', 'GET', 'DELETE'])

# Company page apis
api.add_resource(CompanyPageListAPI, '/company-pages')
api.add_resource(CompanyPageAPI, '/company-pages',
                 methods=['POST'], endpoint='companypagepostapi')
api.add_resource(CompanyPageAPI, '/company-pages/<int:row_id>',
                 methods=['PUT', 'GET', 'DELETE'])

# Global Activity apis
api.add_resource(GlobalActivityGetListApi, '/activities')

# for event calender
api.add_resource(EventCalendarListAPI, '/event-calendars')

# Corporate Announcement
api.add_resource(CorporateAnnouncementListAPI, '/corporate-announcements')
api.add_resource(CorporateAnnouncementNoAuthListAPI,
                 '/corporate-announcements-no-auth')
api.add_resource(CorporateAnnouncementNoAuthAPI,
                 '/corporate-announcements-no-auth/<int:row_id>')
api.add_resource(CorporateAnnouncementAPI, '/corporate-announcements',
                 methods=['POST'], endpoint='corporateannouncementpostapi')
api.add_resource(CorporateAnnouncementAPI,
                 '/corporate-announcements/<int:row_id>',
                 methods=['PUT', 'GET', 'DELETE'])
api.add_resource(CorporateAnnouncementXMLAPI, '/corporate-announcements-xml',
                 methods=['POST'])

# Admin Corporate Announcement
api.add_resource(
    AdminCorporateAnnouncementListAPI, '/admin-corporate-announcements')
api.add_resource(
    AdminCorporateAnnouncementAPI, '/admin-corporate-announcements',
    methods=['POST'], endpoint='admincorporateannouncementpostapi')
api.add_resource(
    AdminCorporateAnnouncementAPI,
    '/admin-corporate-announcements/<int:row_id>',
    methods=['PUT', 'GET', 'DELETE'])
api.add_resource(
    AdminCorporateBulkAnnouncementAPI,
    '/admin-corporate-bulk-announcements',
    methods=['PUT'])
api.add_resource(
    AdminCorporateAnnouncementCategoryListAPI, '/admin-corporate-announcements-category')
api.add_resource(
    AdminCorporationCategoryAPI, '/admin-corporate-announcements-category',
    methods=['POST'], endpoint='admincorporateannouncementcategorypostapi')
api.add_resource(
    AdminCorporationCategoryAPI,
    '/admin-corporate-announcements-category/<int:row_id>',
    methods=['PUT', 'GET', 'DELETE'])

# inquiriy apis
api.add_resource(InquiryListAPI, '/inquiries')
api.add_resource(InquiryContactUsPostAPI, '/inquiries/contact-us',
                 methods=['POST'])
api.add_resource(InquiryPlanPostAPI, '/inquiries/plan', methods=['POST'])
api.add_resource(InquiryAPI, '/inquiries/<int:row_id>', methods=['GET', 'PUT'])

# user verification
api.add_resource(TokenVerificationAPI, '/token-verification')

# user dashboard
api.add_resource(UserDashboardStatsListAPI, '/user-dashboard', methods=['GET'])
api.add_resource(UserEventMonthWiseStatsListAPI, '/user-event-month-wise',
                 methods=["GET"])
api.add_resource(UserMonthWiseEventTypeStatsListAPI, '/user-month-event-type',
                 methods=["GET"])


api.add_resource(UnsubscriptionAPI, '/unsubscription/<string:token>',
                 methods=['POST'], endpoint='unsubscriptionpostapi')
api.add_resource(UserUnsubscriptionAPI, '/preferences',
                 methods=['GET','PUT', 'DELETE','POST'])

api.add_resource(AdminUnsubscriptionAPI,'/admin-unsubscriptions/<int:row_id>',
                 methods=['GET','PUT','DELETE'])
api.add_resource(UnsubscriptionListAPI, '/admin-unsubscriptions',
                 methods=['GET'], endpoint='unsubscriptionlistapi')

api.add_resource(UnsubscribeReasonListAPI, '/unsubscribe-reasons',
                 methods=['GET'])
api.add_resource(UnsubscribeReasonAPI, '/unsubscribe-reasons',
                 methods=['POST'], endpoint= 'unsubscribereasonpostapi')
api.add_resource(UnsubscribeReasonAPI, '/unsubscribe-reasons/<int:row_id>',
                 methods=['GET', 'PUT'])

api.add_resource(
    AdminPublishNotificationListAPI, '/admin-publish-notification',
    methods=['GET'])
api.add_resource(AdminPublishNotificationAPI, '/admin-publish-notification',
                 methods=['POST'], endpoint='adminpublishnotificationpostapi')
api.add_resource(
    AdminPublishNotificationAPI, '/admin-publish-notification/<int:row_id>',
    methods=['GET', 'DELETE'])

# global search
api.add_resource(SearchAPI, '/global_search', methods=['GET'])
# Menus
api.add_resource(MenuListAPI, '/menus')
api.add_resource(MenuAPI, '/menus',
                 methods=['POST'], endpoint='menuspostapi')
api.add_resource(MenuAPI, '/menus/<int:row_id>',
                 methods=['PUT', 'GET', 'DELETE'])
api.add_resource(BulkMenuUpdate, '/update-all-menus')

# Permissions
api.add_resource(PermissionListAPI, '/permissions')
api.add_resource(PermissionAPI, '/permissions',
                 methods=['POST'], endpoint='permissionspostapi')
api.add_resource(PermissionAPI, '/permissions/<int:row_id>',
                 methods=['PUT', 'GET', 'DELETE'])

# current user role
api.add_resource(UserRoleAPI, '/user-role')


# Scheduled Report
api.add_resource(ScheduledReportListAPI, '/scheduled-reports')
api.add_resource(ScheduledReportAPI, '/scheduled-reports',
                 methods=['POST'], endpoint='scheduledreportpostapi')
api.add_resource(ScheduledReportAPI, '/scheduled-reports/<int:row_id>',
                 methods=['PUT', 'GET', 'DELETE'])
api.add_resource(ScheduledReportLogApi, '/scheduled_report_log',
                 methods=['POST'])

# Admin Scheduled reports
api.add_resource(AdminScheduledReportListAPI, '/admin-scheduled-reports')
api.add_resource(AdminScheduledReportUserwiseAPI, '/scheduled-reports-by-user')
api.add_resource(AdminScheduledReportLogListAPI,
                 '/admin-scheduled-reports-log')

# email credential apis
api.add_resource(EmailCredentialAPI, '/email-credential',
                 methods=['GET', 'PUT', 'DELETE'])

# Login log api
api.add_resource(LoginLogListAPI, '/login-logs')

# User activity logs apis
api.add_resource(UserActivityLogListAPI, '/user-activity-logs')
api.add_resource(UserActivityLogAPI, '/user-activity-logs', methods=['POST'])

api.add_resource(ActionVisitCountAPI, '/action-visit-count')
api.add_resource(VisitsActionsOverTimeAPI, '/actions-visits-by-time')
api.add_resource(UserActivityLogRecordListAPI, '/user-activity-logs-record')

# Twitter Feed apis
api.add_resource(TwitterFeedListAPI, '/twitter-feeds')
api.add_resource(
    TwitterSourceFeedAPI, '/twitter-feed-source',
    endpoint='twitterscourcefeedpostapi', methods=['POST'])

api.add_resource(DomainListAPI, '/domains')
api.add_resource(DomainAPI, '/domains',
                 methods=['POST'], endpoint='domainlistpostapi')
api.add_resource(DomainAPI, '/domains/<int:row_id>',
                 methods=['PUT', 'GET', 'DELETE'])

api.add_resource(DomainConfigListAPI, '/domain-configs')
api.add_resource(DomainConfigAPI, '/domain-configs',
                 methods=['POST'], endpoint='domainconfigspostapi')
api.add_resource(DomainConfigAPI, '/domains/<int:row_id>',
                 methods=['PUT', 'GET', 'DELETE'])
api.add_resource(PublishRecordingAPI,
                 '/publish-recording/<int:row_id>',
                 methods=['PUT'])

api.add_resource(ProjectHistoryAdminAnalystAPI, '/project-history/<int:row_id>',
                 methods=['GET'])
api.add_resource(ProjectHistoryAdminAnalystListAPI, '/project-history',
                 methods=['GET'])

# market resources (Market Comment)
api.add_resource(MarketCommentAPI, '/analyst_comment',
                 methods=['POST'], endpoint='marketanalystcommentapi')
api.add_resource(MarketCommentAPI, '/analyst_comment/<int:row_id>',
                 methods=['PUT','DELETE','GET'])
api.add_resource(MarketCommentListAPI, '/analyst_comment',
                 methods=['GET'])
# Market Performance
api.add_resource(MarketPerformanceAPI, '/market_performance',
                 methods=['POST'], endpoint='marketcompanyperformanceapi')
api.add_resource(MarketPerformanceAPI, '/market_performance/<int:row_id>',
                 methods=['DELETE','GET'])
api.add_resource(MarketPerformanceListAPI, '/market_performance',
                 methods=['GET'])

# Distribution List
api.add_resource(DistributionListXLSAPI, '/distribution_list_XLS',
                 methods=['POST'])
api.add_resource(DistributionListFrontEndAPI, '/frontend_distribution_list',
                 methods=['POST'])
api.add_resource(DistributionListAPI, '/distribution_list',
                 methods=['POST'], endpoint='distributionlist')
api.add_resource(DistributionListAPI, '/distribution_list/<int:row_id>',
                 methods=['GET','DELETE','PUT'])
api.add_resource(DistributionListofListAPI, '/distribution_list',
                 methods=['GET'])
api.add_resource(DistributionBulkAPI, '/distribution_bulk_list',
                 methods=['PUT'])
api.add_resource(DistributionBulkDeletAPI, '/distribution_bulk_delete',
                 methods=['PUT'])

# EmailLogs List
api.add_resource(EmailLogListAPI, '/emaillog-list',
                 methods=['GET'])
api.add_resource(EmailRecordcount, '/emaillog-record',
                 methods=['GET'])

# email statics
api.add_resource(EmailStatic,'/email_statics',methods=['POST'])
api.add_resource(EmailStaticListAPI,'/email-event-statics',methods=['GET'])

# Activity
api.add_resource(ActivityAPI, '/activity',
                 methods=['POST'],endpoint='useractivityapi')
api.add_resource(ActivityAPI, '/activity/<int:row_id>',
                 methods=['GET', 'PUT', 'DELETE'])
api.add_resource(ActivityList, '/activity-list')

# Goaltracker
api.add_resource(GoalTrackerAPI, '/goaltracker',
                 methods=['POST'],endpoint='goaltrackerapitest')
api.add_resource(GoalTrackerAPI, '/goaltracker/<int:row_id>',
                 methods=['GET', 'PUT', 'DELETE'])
api.add_resource(GoalTrackerList, '/goaltracker-list')

# Activity-Type
api.add_resource(ActivityTypeAPI, '/activity-type',
                 methods=['POST'],endpoint='activitytype')
api.add_resource(ActivityTypeAPI, '/activity-type/<int:row_id>',
                 methods=['GET', 'PUT', 'DELETE'])
api.add_resource(ActivityTypeListAPI, '/activity-type-list')

# Activity Reresenattion
api.add_resource(RepresentativeAPI, '/represenatative-list')

# Activity institution
api.add_resource(ActivityIntituteFactSetList, '/factset-participants-list')

# Ir Module 
api.add_resource(IrModuleAPI, '/ir-module',
                 methods=['POST'], endpoint='irmodule')
api.add_resource(IrModuleAPI, '/ir-module/<int:row_id>',
                 methods=['PUT','DELETE','GET'])
api.add_resource(IrModuleListAPI, '/ir-module-list',
                 methods=['GET'])
api.add_resource(IrModuleAdminListAPI, '/ir-module-admin-list',
                 methods=['GET'])

# ir module heading
api.add_resource(IrModuleHeadingAPI, '/ir-module-heading',
                 methods=['POST'], endpoint='irmoduleheading')
api.add_resource(IrModuleHeadingAPI, '/ir-module-heading/<int:row_id>',
                 methods=['PUT','DELETE','GET'])
api.add_resource(IrModuleHeadingListAPI, '/ir-module-heading-list',
                 methods=['GET'])

# cron_job APIs
api.add_resource(CronListAPI, '/cron-job-list',
                 methods=['GET'])
api.add_resource(CronJobAPI, '/cron-job/<int:row_id>',
                 methods=['GET','PUT'])
api.add_resource(CronActivity, '/cron-activity/<int:row_id>',
                 methods=['PUT'])
#bse feed api
api.add_resource(BSEFeedAPI, '/bse-feed/<int:row_id>',methods=['GET'])
api.add_resource(BSEFeedListAPI, '/bse-feed', methods=['GET'])
api.add_resource(BSEFeedStatsAPI, '/bse-feed-stats', methods=['GET'])

#personalised video api
api.add_resource(AdminPersonalisedVideoAPI, '/personalised-video',
                 methods=['POST'], endpoint='adminpersonalisedvideopostapi')
api.add_resource(AdminPersonalisedVideoAPI, '/personalised-video/<int:row_id>',
                 methods=['PUT', 'DELETE', 'GET'])
api.add_resource(PersonalisedVideoListAPI, '/personalised-video-list',
                 methods=['GET'])
api.add_resource(PersonalisedVideoAPI, '/personalised-video/verify/<string:token>',
                 methods=['GET'])
api.add_resource(PersonalisedVideoAPI, '/personalised-video/<string:token>',
                 methods=['PUT'], endpoint='personalisedvideoputapi')
api.add_resource(PersonalisedVideoLogListAPI, '/personalised-video-invitee-logs')

#health check api
api.add_resource(HealthCheckAPI, '/health')
api.add_resource(CorporateAnnouncementCategoryListAPI, '/corporate-categories')

# descriptor api's
api.add_resource(
    AdminBSEDescriptorListAPI, '/admin-bse-descriptor')
api.add_resource(
    AdminBSEDescriptorAPI, '/admin-bse-descriptor',
    methods=['POST'], endpoint='adminbsedescriptorpostapi')
api.add_resource(
    AdminBSEDescriptorAPI,
    '/admin-bse-descriptor/<int:row_id>',
    methods=['PUT', 'GET', 'DELETE'])

# result tracker group api
api.add_resource(
    ResultTrackerGroupListAPI, '/result-tracker-group', methods=['GET'])
api.add_resource(ResultTrackerGroupAPI, '/result-tracker-group',
                 methods=['POST'], endpoint='resulttrackergrouppostapi')
api.add_resource(ResultTrackerGroupAPI, '/result-tracker-group/<int:row_id>',
                 methods=['PUT', 'GET', 'DELETE'])
api.add_resource(ResultTrackerGroupBulkAPI, '/result-tracker-group-bulk-edit',
                 methods=['PUT'])

# result tracker group company api
api.add_resource(
    ResultTrackerGroupCompaniesListAPI, '/result-tracker-group-company')
api.add_resource(ResultTrackerGroupCompaniesAPI, '/result-tracker-group-company',
                 methods=['POST'], endpoint='resulttrackergroupcomapniespostapi')
api.add_resource(ResultTrackerGroupCompaniesAPI, '/result-tracker-group-company/<int:row_id>',
                 methods=['PUT', 'GET', 'DELETE'])
api.add_resource(ResultTrackerGroupCompaniesBulkEditAPI, '/result-tracker-group-companies-bulk-edit',
                 methods=['PUT'])
api.add_resource(ResultTrackerGroupCompaniesBulkDeleteAPI, '/result-tracker-group-companies-bulk-delete',
                 methods=['PUT'])

# AudioTranscribeListAPI, AudioTranscribeAPI
api.add_resource(
    AudioTranscribeListAPI, '/audio-transcribe-list')
api.add_resource(AudioTranscribeAPI, '/audio-transcribe',
                 methods=['POST'], endpoint='audiotranscribepostapi')
api.add_resource(AudioTranscribeAPI, '/audio-transcribe/<int:row_id>',
                 methods=['GET', 'DELETE'])
