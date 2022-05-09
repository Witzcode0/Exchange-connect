"""
Helpers for corporate announcement
"""

from sqlalchemy import and_
from sqlalchemy.orm import load_only

from app.resources.follows.models import CFollow


def check_cfollow_exists(company_id, user_id):
    """
    Check in cfollow company id exists or not
    :param company_id: company id which following
    :param user_id: user_id which is follower
    :return:
    """
    error = None
    cfollow_data = None

    cfollow_data = CFollow.query.filter(and_(
        CFollow.sent_by == user_id,
        CFollow.company_id == company_id)).options(load_only(
            'row_id')).first()

    if not cfollow_data:
        error = 'Cfollow not found'
        return cfollow_data, error

    return cfollow_data, error
