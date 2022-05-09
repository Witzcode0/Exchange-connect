"""
Helper classes/functions for "user settings" package.
"""

from sqlalchemy.orm import load_only

from app.resources.user_settings.models import UserSettings
from app.resources.industries.models import Industry
from app.resources.sectors.models import Sector


def create_default_user_settings(user_data):
    """
    creating default user setting while creating a new user
    :param user_data:
    :return: user object
    """
    if not user_data.settings:
        user_data.settings = UserSettings()
    # adding all sector row_ids to the search_privacy_sector in
    # user_settings and sector_ids in user_profile by default
    sector_data = [f.row_id for f in Sector.query.options(
        load_only('row_id')).all()]
    user_data.settings.search_privacy_sector = sector_data
    user_data.profile.sector_ids = sector_data
    # adding all industry row_ids to the search_privacy_industry in
    # user_settings and industry_ids in user_profile by default
    industry_data = [f.row_id for f in Industry.query.options(
        load_only('row_id')).all()]
    user_data.settings.search_privacy_industry = industry_data
    user_data.profile.industry_ids = industry_data

    return user_data
