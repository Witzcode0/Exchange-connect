"""
Activity related tasks
"""

import datetime

from flask import current_app

from app import db
from app.activity.activities.models import Activity
from app.activity.activities import constants as ACTIVITY
from app.resources.reminders import constants as REMINDER
from app.resources.reminders.models import Reminder

from queueapp.tasks import celery_app, logger


@celery_app.task(bind=True, ignore_result=True)
def manage_activity_reminder(self, result, row_id, *args, **kwargs):
    """
    Add/remove/update the reminder row of the activity whenever an activity is
    added/updated

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id
    """
    if result:
        try:
            model = Activity.query.get(row_id)
            if not model or not model.started_at:
                # remove reminders if any
                Reminder.query.filter(
                    Reminder.activity_id == row_id).delete(
                    synchronize_session=False)
                return True

            # add the default reminder always, if not already there
            def_reminder = Reminder.query.filter(
                Reminder.activity_id == row_id,
                Reminder.reminder_sys_type == REMINDER.RST_DEFAULT).first()
            if not def_reminder:
                # add the default reminder
                # check start date, and if start date is atleast 1 minute
                # before
                if (model.started_at - datetime.datetime.utcnow() > (
                        current_app.config['DEF_REMINDER_BEFORE'] +
                        datetime.timedelta(minutes=1))):
                    def_reminder = Reminder(
                        user_id=model.created_by, activity_id=row_id,
                        reminder_sys_type=REMINDER.RST_DEFAULT)
                    def_reminder.activity = model
                    def_reminder.calculate_next_at()
                    db.session.add(def_reminder)
                    db.session.commit()
            # else:
            #     # started_at could have changed, so recalculate the next_at
            #     if (model.started_at - datetime.datetime.utcnow() > (
            #             current_app.config['DEF_REMINDER_BEFORE'] +
            #             datetime.timedelta(minutes=1))):
            #         def_reminder.activity = model
            #         def_reminder.calculate_next_at()
            #         db.session.add(def_reminder)
            #         db.session.commit()
            #     else:
            #         db.session.delete(def_reminder)
            #         db.session.commit()

            # find custom reminder
            existed = False
            cus_reminder = Reminder.query.filter(
                Reminder.activity_id == row_id,
                Reminder.reminder_sys_type == REMINDER.RST_USER).first()
            if cus_reminder:
                existed = True
            # create/delete the custom reminder row
            if all([model.reminder_time, model.reminder_unit]):
                if model.reminder_unit == ACTIVITY.RM_WEEKS:
                    next_at = model.started_at - datetime.timedelta(days=model.reminder_time*7)
                else:
                    before = {model.reminder_unit: model.reminder_time}
                    next_at = model.started_at - datetime.timedelta(**before)
                # model.reminder_start = next_at
                # check start date, and if start date is atleast the minimum
                if model.started_at > next_at:
                    if not cus_reminder:
                        cus_reminder = Reminder(
                            user_id=model.created_by, activity_id=row_id,
                            reminder_sys_type=REMINDER.RST_USER)
                        cus_reminder.activity = model
                    cus_reminder.next_at = next_at

                    if next_at < model.started_at:
                        db.session.add(cus_reminder)
                        db.session.commit()

                        if def_reminder:
                            db.session.delete(def_reminder)
                            db.session.commit()
                    else:
                        if existed:
                            db.session.delete(cus_reminder)
                            db.session.commit()
                        if def_reminder:
                            db.session.delete(def_reminder)
                            db.session.commit()
                else:
                    if existed:
                        db.session.delete(cus_reminder)
                        db.session.commit()
                    if def_reminder:
                        db.session.delete(def_reminder)
                        db.session.commit()

            else:
                # unset the reminder dates, frequency
                # model.reminder_start = None
                # model.reminder_frequency = None
                # db.session.add(model)
                # db.session.commit()
                # delete custom reminder if reminder unset
                if cus_reminder:
                    db.session.delete(cus_reminder)
                    db.session.commit()

            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result
