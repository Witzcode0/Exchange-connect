"""
Helper classes/functions for "goaltracker" package.
"""

from sqlalchemy.orm import load_only

from app.activity.activities.models import Activity
from app.activity.activities import constants as ACTIVITY
from app.common.utils import time_converter



def goal_count_update(data, method='GET'):
    """
    update goal count according to activity data

    :param data:
        the goaltracker model object

    :param method:
        requested method

    :return: goal_count, and completed_activity_ids
    """
    goal_count = 0
    completed_activity_ids = []
    # If method is a post or put only then time convert called
    if method == 'POST' or method == 'PUT':
        started_at = time_converter(data.started_at, 'UTC', 'Asia/Kolkata')
        data.started_at = started_at.strftime("%Y-%m-%dT%H:%M:%SZ")

        ended_at = time_converter(data.ended_at, 'UTC', 'Asia/Kolkata')
        data.ended_at = ended_at.strftime("%Y-%m-%dT%H:%M:%SZ")

    activities = Activity.query.filter(
        Activity.created_by == data.created_by,
        Activity.activity_type == data.activity_type,
        Activity.started_at.between(
            data.started_at, data.ended_at)).options(load_only(
            'row_id', 'created_by', 'started_at',
            'ended_at')).filter(Activity.deleted.is_(False))

    completed_activity_ids = [act.row_id for act in activities]
    goal_count = len(completed_activity_ids)

    return goal_count, completed_activity_ids
