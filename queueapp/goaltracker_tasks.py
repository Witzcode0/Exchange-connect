"""
goaltracker related task
"""

import dateutil

from sqlalchemy.orm import load_only

from app import db
from app.resources.goaltrackers.models import GoalTracker
from app.activity.activities.models import Activity
from app.activity.activities import constants as ACTIVITY

from queueapp.tasks import celery_app, logger


@celery_app.task(bind=True, ignore_result=True)
def manage_related_goaltrackers(self, result, row_id, started_at,
                                activity_type, *args, **kwargs):
    """
    Update goal trackers when activities are edited, i.e started_at changes, or
    activity_type changes

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id
    :param started_at:
        the original started_at value, used to match the original goals
    :param activity_type:
        the original activity_type value, used to match the original goals
    """

    if result:
        result = False
        try:
            activity = Activity.query.get(row_id)
            if not activity:  # just being extra careful, not really required
                return True

            org_started_at = dateutil.parser.parse(started_at)
            if org_started_at.date() == activity.started_at.date():
                # date has not changed
                if activity_type == activity.activity_type:
                    # activity type has also not changed
                    return True
            if activity.status != ACTIVITY.EST_CD:
                # activity is not completed, so it would not be tracked in
                # goal anyway
                return True

            # either date or activity type has changed, so check goals
            # remove the activity_id from old goals, and reduce count
            old_goals = GoalTracker.query.filter(
                GoalTracker.created_by == activity.created_by,
                GoalTracker.activity_type == activity_type,
                GoalTracker.started_at <= org_started_at.date(),
                GoalTracker.ended_at >= org_started_at.date()).all()
            for oldg in old_goals:
                if not oldg.completed_activity_ids:
                    # empty or None, so nothing to do
                    continue
                if row_id not in oldg.completed_activity_ids:
                    continue
                oldg.completed_activity_ids = [
                    rid for rid in oldg.completed_activity_ids
                    if rid != row_id]
                oldg.goal_count = len(oldg.completed_activity_ids)
                db.session.add(oldg)
                db.session.commit()

            # add the activity_id to new goals, and increase count
            new_goals = GoalTracker.query.filter(
                GoalTracker.created_by == activity.created_by,
                GoalTracker.activity_type == activity.activity_type,
                GoalTracker.started_at <= activity.started_at.date(),
                GoalTracker.ended_at >= activity.started_at.date()).all()
            for newg in new_goals:
                if not newg.completed_activity_ids:
                    newg.completed_activity_ids = []
                if row_id in newg.completed_activity_ids:
                    # already in list
                    continue
                newg.completed_activity_ids =\
                    newg.completed_activity_ids[:] + [row_id]
                newg.goal_count = len(newg.completed_activity_ids)
                db.session.add(newg)
                db.session.commit()

            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)

    return result


@celery_app.task(bind=True, ignore_result=True)
def manage_goaltrackers_on_status_change(
        self, result, row_id, completed_ids, incomplete_ids, *args, **kwargs):
    """
    Update goal trackers when multiple activity statuses are updated.

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the goal for which these were marked, this goal will be left untouched
    :param completed_ids:
        the row ids of completed activities
    :param incomplete_ids:
        the row ids of incomplete activities
    """

    if result:
        result = False
        try:
            goal = GoalTracker.query.get(row_id)
            # first handle the completed ones
            if completed_ids:
                completed_acts = Activity.query.filter(
                    Activity.row_id.in_(completed_ids)).options(load_only(
                        'row_id', 'started_at', 'activity_type')).all()
                for cact in completed_acts:
                    # for each completed activity find the related goals
                    goals_for_complete = GoalTracker.query.filter(
                        GoalTracker.created_by == goal.created_by,
                        GoalTracker.activity_type == cact.activity_type,
                        GoalTracker.started_at <= cact.started_at.date(),
                        GoalTracker.ended_at >= cact.started_at.date()).all()
                    for gfc in goals_for_complete:
                        if gfc.row_id == row_id:
                            continue
                        # for each related goal, increase the count, and add to
                        # ids list
                        if not gfc.completed_activity_ids:
                            gfc.completed_activity_ids = []
                        if cact.row_id in gfc.completed_activity_ids:
                            # already in list
                            continue
                        gfc.completed_activity_ids =\
                            gfc.completed_activity_ids[:] + [cact.row_id]
                        gfc.goal_count = len(gfc.completed_activity_ids)
                        db.session.add(gfc)
                        db.session.commit()

            # second handle the incomplete ones
            if incomplete_ids:
                # find all goals where these were counted as completed
                incomplete_acts = Activity.query.filter(
                    Activity.row_id.in_(incomplete_ids)).options(load_only(
                        'row_id', 'started_at', 'activity_type')).all()
                for iact in incomplete_acts:
                    # for each incomplete activity find the related goals
                    goals_for_incomplete = GoalTracker.query.filter(
                        GoalTracker.created_by == goal.created_by,
                        GoalTracker.activity_type == iact.activity_type,
                        GoalTracker.started_at <= iact.started_at.date(),
                        GoalTracker.ended_at >= iact.started_at.date()).all()
                    for gfi in goals_for_incomplete:
                        if gfi.row_id == row_id:
                            continue
                        # for each related goal, manage the count, and ids list
                        if not gfi.completed_activity_ids:
                            # empty or None, so nothing to do
                            continue
                        if iact.row_id not in gfi.completed_activity_ids:
                            # already not counted
                            continue
                        gfi.completed_activity_ids = [
                            rid for rid in gfi.completed_activity_ids
                            if rid != iact.row_id]
                        gfi.goal_count = len(gfi.completed_activity_ids)
                        db.session.add(gfi)
                        db.session.commit()

            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)

    return result
