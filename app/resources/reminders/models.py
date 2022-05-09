"""
Models for "reminders" package.
Reminders is a transient table, and its rows exist as long as its activity
is still active, or incomplete, once the activity is complete/ or start data/
end date is passed, then the respective rows are removed.
"""

import datetime

from flask import current_app

from app import db
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString, LCString,CastingArray
from app.resources.reminders import constants as REMINDER
from app.activity.activities import constants as ACTIVITY


class Reminder(BaseModel):

    __tablename__ = 'reminder'

    user_id = db.Column(db.Integer, db.ForeignKey(
        'user.id', name='reminder_user_id_fkey', ondelete='CASCADE'), nullable=False)
    activity_id = db.Column(db.Integer, db.ForeignKey(
        'activity.id', name='reminder_activity_id_fkey', ondelete='CASCADE'), nullable=False)
    reminder_sys_type = db.Column(ChoiceString(
        REMINDER.REMINDER_SYS_TYPES_CHOICES), nullable=False)

    # when is it next (specific upto minute)
    next_at = db.Column(db.DateTime, nullable=False)
    # #TODO: task for adding notification, we might not need this depending on
    # implementation
    current_task_id = db.Column(db.String())

    # relationship
    activity = db.relationship('Activity')
    user = db.relationship('User')

    def __init__(self, user_id=None, activity_id=None, reminder_sys_type=None,
                 *args, **kwargs):
        self.user_id = user_id
        self.activity_id = activity_id
        self.reminder_sys_type = reminder_sys_type
        super(Reminder, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Reminder row_id=%r, user_id=%r, sys_type=%r>' % (
            self.row_id, self.user_id, self.reminder_sys_type)

    def calculate_next_at(self, activity=None, populate_self=True,
                          next_at=None):
        """
        Calculates the next at time for a reminder

        :param activity:
            pass the related activity, useful during creation
        :param populate_self:
            boolean indicating whether to populate the next_at value
        :param next_at:
            pass a current next_at value if the next next_at is to be
            calculated
        """
        activity = activity or self.activity
        if self.reminder_sys_type == REMINDER.RST_DEFAULT:
            # next_at will be 30 minutes prior to started_at
            next_at = activity.started_at - current_app.config[
                'DEF_REMINDER_BEFORE']
        elif self.reminder_sys_type == REMINDER.RST_USER:
            # reminder_frequency
            next_at_delta = datetime.timedelta(minutes=30)
            if activity.reminder_unit == ACTIVITY.RM_MINS:  # weekly
                if activity.reminder_time:
                    next_at_delta = datetime.timedelta(minutes=activity.reminder_time)
            if activity.reminder_unit == ACTIVITY.RM_HOURS:  # weekly
                if activity.reminder_time:
                    next_at_delta = datetime.timedelta(hours=activity.reminder_time)
            if activity.reminder_unit == ACTIVITY.RM_DAYS:  # weekly
                if activity.reminder_time:
                    next_at_delta = datetime.timedelta(days=activity.reminder_time)
            elif activity.reminder_unit == ACTIVITY.RM_WEEKS:  # daily
                if activity.reminder_time:
                    days = activity.reminder_time * 7
                    next_at_delta = datetime.timedelta(days=days)
            if not next_at:  # reset first reminder
                next_at = activity.started_at - next_at_delta
            # next_at = next_at + next_at_delta

        if populate_self and next_at:
            self.next_at = next_at

        return next_at
