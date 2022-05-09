"""
The main commands module
"""

import sys

from gevent import monkey



monkey.patch_all()  # required for socketio

from flask_script import Manager
from werkzeug.debug import get_current_traceback

from flask_migrate import MigrateCommand

# import app related components
if __name__ == "__main__" and __package__ is None:
    import os
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)
    import commands
    __package__ = "commands"
from app import create_app
from commands.deployment_setup import SetupDB, SetupDefaultDB, SetupTestDemoDB
from commands.setup_custom_ses_email import (
    CreateCustomSESVerificationTemplate, UpdateCustomSESVerificationTemplate)
from commands.newsfeed import update_feeditems, maintain_feeditems, delete_index
from commands.companies.import_companies_data import ImportCompanyData
from commands.surveys.close_surveys import CloseSurvey
from commands.events.update_counts_events import UpdateCountsInEvents
from commands.feeds.add_feeds_posts_history import AddFeedPostHistory
from commands.time_zones.import_time_zones import ImportTimeZones
from commands.state_cities.import_states_cities import ImportStatesCities
from commands.state_cities.remove_missing_countries_states import (
    RemoveCountriesStates)
from commands.accounts.import_account_news import ImportAccountsNews
from commands.users.update_users_account_type_id import (
    UpdateUsersAccountIdType)
from commands.sector_industry.update_sector_industry import \
    UpdateSectorIndustryAccountProfile
from commands.sector_industry.update_sector_industry import \
    UpdateSectorIndustryUserProfile
from commands.users.update_user_settings import UpdateUserSettings
from commands.users.update_user_profile_thumbnail import \
    UpdateUserProfileThumbnails
from commands.accounts.import_accounts_data import ImportAccountData
from commands.accounts.update_market_cap import UpdateMarketCapData
from commands.accounts.update_account_stats import UpdateAccountStats
from commands.account_profiles.update_sector_industry import \
    UpdateSectorIndustryData
from commands.sector_industry.update_sector_industry import \
    UpdateSectorIndustryCompany
from commands.update_sequence.update_sequence_id import UpdateSequenceId
from commands.contacts.add_default_contacts_to_user import (
    AddDefaultContactsToUser)
from commands.management_profiles.update_management_profile_sequence_id \
    import UpdateManagementProfileSequenceID
from commands.users.update_user_sequence_id import UpdateUserSequenceID
from commands.users.update_user_manager import UpdateUserManagerRole
from commands.users.update_users_token_key import UpdateUsersTokenKey
from commands.accounts.update_account_company_market_cap import (
    UpdateAccountCompanyMarketCap)
from commands.account_settings.add_settings import AddDefaultSettings
from commands.events.update_caevent_account_id import UpdateCAEventAccountID
from commands.corporate_announcements.add_corporate_announcements import \
    AddCorporateAnnouncement
from commands.corporate_announcements.add_corporate_announcement_category import \
    AddCorporateAnnouncementCategory
from commands.accounts.update_account_by_isin_excel import (
    UpdateAccountByISINExcel)
from commands.elastic_reindex import ElasticReindex
from commands.users.update_user_notifications_count import (
    UpdateUserNotificationsCount)
from commands.management_profiles.update_management_profile_thumbnail import (
    UpdateManagementProfileThumbnails)
from commands.unsubscrition.create_unsubscrition_for_users import (
    CreateUnsubscriptionForExitsUsers)
from commands.users.add_user_settings import AddUserSettings
from commands.accounts.delete_update_accounts import DeleteUpdateAccounts
from commands.accounts.import_account_keywords import ImportAccountKeywords
from commands.scheduled_reports.send_scheduled_reports import (
    SendScheduleReports)
from commands.scheduled_reports.deactivate_scheduled_reports import (
    DeactivateScheduleReports)
from commands.scheduled_reports.reset_report_downloaded import (
    ResetReportDownloaded)
from commands.newsfeed.delete_feeditems import DeleteFeedItems
from commands.twittersfeed.update_feeditems import FetchTwitterFeed
from commands.newsfeed.news_tagging import TagNews
from commands.accounts.file_parsing import FileParsing
from commands.newsfeed.parse_news_desc import ParseNewsDesc
from commands.state_cities.update_city_state_country import (
    UpdateCityStateCountry)
from commands.esg_frameworks.import_esg_parameters import (
    ImportESGParametersByExcel)
from commands.email_automation.user_email_automation import SendNewsEmail
from commands.email_automation.uae_user_email_automation import SendUAENewsEmail

from commands.reminders.maintain_new_reminders import UpdateAndNotifyReminder
from commands.reminders.maintain_old_reminders import DeleteOldReminders
from commands.bsecorpfeed.update_feeditems import FetchBseFeed
from commands.corporate_announcements.delete_repeated_feed import DeleteRepeatedFeed
from commands.corporate_announcements.update_corporate_announcement_date import Updatecadate
from commands.bsecorpfeed.update_bse_date import UpdateBseDate
from commands.bsecorpfeed.update_ec_category import Updatebseeccat
from commands.corporate_announcements.update_new_category import UpdateCACategory
from commands.email_automation.bse_announcement_automation import SendBseAnnouncementEmail
from commands.research_reports.add_parsing_files_values import AddParsingFiles
from commands.result_tracker.add_favourites_watchlist import AddWatchlist
from commands.bsecorpfeed.update_result_tracker_companies import UpdateResultComp
from commands.bse_mf_etf.migrate_feeditems import MigrateMfEtf

flaskapp = create_app('commands_config')
manager = Manager(flaskapp)


def configure_extension_commands():
    """
    Configure commands from any extensions
    """

    # flask-migrate
    manager.add_command('db', MigrateCommand)


def configure_setup_commands():
    """
    Configure commands for any setup required for deployment, testing
    """

    # db, alembic version
    manager.add_command('setup_db', SetupDB)
    # default account, user, roles setup
    manager.add_command('setup_default_db', SetupDefaultDB)
    manager.add_command('setup_test_demo_db', SetupTestDemoDB)
    # setup default custom ses verification email template
    manager.add_command('create_custom_ses_verification_template',
                        CreateCustomSESVerificationTemplate)
    manager.add_command('update_custom_ses_verification_template',
                        UpdateCustomSESVerificationTemplate)


def configure_crons():
    """
    Add any cron job functions
    """
    manager.add_command('send_bse_announcements', SendBseAnnouncementEmail)
    manager.add_command('update_bse_feed', FetchBseFeed)
    manager.add_command('update_feeditems', update_feeditems.FetchNews())
    manager.add_command('delete_indexitems', delete_index.DeleteIndex())
    manager.add_command(
        'maintain_feeditems', maintain_feeditems.DeleteFeedItems())
    manager.add_command('close_surveys', CloseSurvey)
    manager.add_command('update_account_company_market_cap',
                        UpdateAccountCompanyMarketCap)
    manager.add_command('send_scheduled_reports', SendScheduleReports)
    manager.add_command('deactivate_scheduled_reports',
                        DeactivateScheduleReports)
    manager.add_command('reset_report_downloaded',
                        ResetReportDownloaded)
    manager.add_command('update_twitter_feed', FetchTwitterFeed)
    manager.add_command('send_news_email', SendNewsEmail)
    manager.add_command('send_UAE_news_email', SendUAENewsEmail)
    # maintain reminders
    manager.add_command('generate_new_reminders',UpdateAndNotifyReminder)
    manager.add_command('delete_old_reminders', DeleteOldReminders)


def configure_fixes():
    """
    Add any one time use fix commands
    """
    manager.add_command('update_counts_events', UpdateCountsInEvents)
    manager.add_command('add_feeds_posts_history', AddFeedPostHistory)
    manager.add_command('import_time_zones', ImportTimeZones)
    manager.add_command('import_states_cities', ImportStatesCities)
    manager.add_command(
        'update_users_account_id_type', UpdateUsersAccountIdType)
    manager.add_command('update_sector_industry_account_profile',
                        UpdateSectorIndustryAccountProfile)
    manager.add_command('update_sector_industry_user_profile',
                        UpdateSectorIndustryUserProfile)
    manager.add_command('update_sector_industry_company',
                        UpdateSectorIndustryCompany)
    manager.add_command('update_user_settings', UpdateUserSettings)
    manager.add_command('remove_countries_states', RemoveCountriesStates)
    manager.add_command('update_sequence_id', UpdateSequenceId)
    manager.add_command('add_default_contacts_to_user',
                        AddDefaultContactsToUser)
    manager.add_command('update_user_profile_thumbnail',
                        UpdateUserProfileThumbnails)
    manager.add_command('update_management_profile_sequence_id',
                        UpdateManagementProfileSequenceID)
    manager.add_command('update_account_stats', UpdateAccountStats)
    manager.add_command('update_user_sequence_id', UpdateUserSequenceID)
    manager.add_command('update_user_manager_role', UpdateUserManagerRole)
    manager.add_command('add_default_settings', AddDefaultSettings)
    manager.add_command('update_caevent_account_ids', UpdateCAEventAccountID)
    manager.add_command('add_corporate_announcement', AddCorporateAnnouncement)
    manager.add_command('add_corporate_announcement_category', AddCorporateAnnouncementCategory)
    manager.add_command('update_users_token_key', UpdateUsersTokenKey)
    manager.add_command('update_user_notifications_count', UpdateUserNotificationsCount)
    manager.add_command('update_management_profile_thumbnail', UpdateManagementProfileThumbnails)
    manager.add_command('import_account_news', ImportAccountsNews)
    manager.add_command('add_user_settings', AddUserSettings)
    manager.add_command(
        'create_unsubscription_for_users', CreateUnsubscriptionForExitsUsers)

    manager.add_command('import_account_keywords', ImportAccountKeywords)
    manager.add_command('file_parsing', FileParsing)
    manager.add_command('update_account_by_isin_excel',
                        UpdateAccountByISINExcel)
    manager.add_command('parse_news_desc', ParseNewsDesc)
    manager.add_command('delete_rep_feed', DeleteRepeatedFeed)
    manager.add_command('update_ca_date', Updatecadate)
    manager.add_command('update_bse_date', UpdateBseDate)
    manager.add_command('update_bse_ec_category', Updatebseeccat)
    manager.add_command('update_ca_category', UpdateCACategory)
    manager.add_command('add_watchlist', AddWatchlist)


def configure_extras():
    """
    Add any extra commands
    """
    manager.add_command('add_parsing_files', AddParsingFiles)
    manager.add_command('import_companies_data', ImportCompanyData)
    manager.add_command('prepopulate_accounts', ImportAccountData)
    manager.add_command('update_market_cap_account_profile',
                        UpdateMarketCapData)
    manager.add_command('update_sector_industry_account_profile',
                        UpdateSectorIndustryData)
    manager.add_command('update_account_company_market_cap',
                        UpdateAccountCompanyMarketCap),
    manager.add_command('elastic_reindex', ElasticReindex)
    manager.add_command('delete_update_accounts', DeleteUpdateAccounts)
    manager.add_command('delete_feeditems', DeleteFeedItems)
    manager.add_command('news_tagging', TagNews)

    manager.add_command('update_city_state_country',
                        UpdateCityStateCountry)
    manager.add_command('import_esg_parameters', ImportESGParametersByExcel)
    manager.add_command('update_result', UpdateResultComp)
    manager.add_command('migrate_mf', MigrateMfEtf)


if __name__ == "__main__":
    try:
        configure_extension_commands()
        configure_setup_commands()
        configure_crons()
        configure_fixes()
        configure_extras()
        manager.run()
    except Exception as e:
        track = get_current_traceback(skip=1, show_hidden_frames=True,
                                      ignore_system_exceptions=False)
        msg = 'Excp = ' + str(e) + '\r\n' + track.plaintext
        print(msg)
        sys.exit(1)
