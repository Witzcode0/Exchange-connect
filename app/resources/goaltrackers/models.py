"""
Models for "goaltracker" package.
"""

import datetime

from app import db
from sqlalchemy.dialects.postgresql import JSONB

from app.base.models import BaseModel
from app.base.model_fields import ChoiceString, LCString,CastingArray
from app.activity.activities import constants as ACTIVITY
from app.activity.activities.models import Activity


class GoalTracker(BaseModel):

    __tablename__ = 'goaltracker'

    created_by = db.Column(db.Integer, db.ForeignKey(
        'user.id', name='goaltracker_created_by_fkey'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey(
        'account.id', name='goaltracker_account_id_fkey'), nullable=False)

    # goaltracker details
    # as we are storing datetime, remember to use date values to check ranges
    started_at = db.Column(db.DateTime, nullable=False)
    ended_at = db.Column(db.DateTime, nullable=False)
    activity_type = db.Column(db.Integer, db.ForeignKey(
        'activity_type.id', name='activity_type_created_by_fkey'), nullable=False)
    target = db.Column(db.Integer, nullable=False)
    goal_name = db.Column(db.String(128))

    # multiple_cities = db.Column(CastingArray(JSONB))

    goal_count = db.Column(db.Integer)
    completed_activity_ids = db.Column(db.ARRAY(db.Integer))

    activity_types = db.relationship('ActivityType', backref=db.backref(
        'activity_type_user_goaltracker', uselist=True),
        primaryjoin='GoalTracker.activity_type == ActivityType.row_id')
    creator = db.relationship('User', backref=db.backref(
        'goaltracker_list_creator', lazy='dynamic'),
    foreign_keys='GoalTracker.created_by')

    tracked_activities = None

    def __init__(self, started_at=None, ended_at=None, target=None,
                 created_by=None, account_id=None, *args, **kwargs):
        self.started_at = started_at
        self.ended_at = ended_at
        self.target = target
        self.created_by = created_by
        self.account_id = account_id
        super(GoalTracker, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<GoalTracker %r>' % self.target

    def load_tracked_activities(self):
        """
        Loads the tracked activities of this goal
        """
        if not self.tracked_activities:
            self.tracked_activities = []
            self.tracked_ids = []

            filters = [Activity.created_by == self.created_by,
                       Activity.activity_type == self.activity_type,
                       Activity.started_at.between(
                           self.started_at,
                           self.ended_at + datetime.timedelta(days=1))]
            
            for act in Activity.query.filter(*filters).all():
                self.tracked_ids.append(act.row_id)
                self.tracked_activities.append(act)

        return self.tracked_activities
