"""
Helper classes/functions for "follows" package.
"""

from sqlalchemy import and_

from app.resources.follows.models import CFollow


def check_company_follow_exists(data):
    """
    check if "sent_by" and "company_id" follow already exists

    :param data:
        company follow object
    :return:
        empty string in case of no errors, else error message string
    """

    company_follow_data = CFollow.query.filter(and_(
        CFollow.company_id == data.company_id), (
        CFollow.sent_by == data.sent_by)).first()

    if company_follow_data:
        return 'Already exists'

    return ''
