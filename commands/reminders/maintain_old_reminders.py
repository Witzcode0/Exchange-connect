import datetime

from flask_script import Command, Option
from sqlalchemy import or_
from sqlalchemy.orm import load_only

from app import db
from app.activity.activities.models import Activity
from app.resources.reminders.models import Reminder


class DeleteOldReminders(Command):
    """
    Command to remove expired reminders, run once a day

    :arg verbose:
        print progress
    :arg dry:
        dry run
    """
    option_list = [
        Option('--verbose', '-v', dest='verbose', action='store_true',
               default=False),
        Option('--dry', '-dry', dest='dry', action='store_true',
               default=False),
    ]

    def run(self, verbose, dry):
        curr_time = datetime.datetime.utcnow()
        curr_day = curr_time.replace(hour=0, minute=0, second=0, microsecond=0)
        if verbose:
            print('---' + str(curr_time) + '---')
            print('Remove expired activity reminders/expired reminders...')

        try:
            # 1. delete all obvious expired reminders, i.e all whose next_at
            # was yesterday
            reminders1 = Reminder.query.filter(Reminder.next_at < curr_day)
            if not dry:
                reminders1.delete(synchronize_session=False)
                db.session.commit()

            # 2. delete all expired activity reminders, i.e all whose activity
            # has ended_at as yesterday or started_at as yesterday
            old_activities = Activity.query.filter(or_(
                Activity.started_at < curr_day,
                Activity.ended_at < curr_day)).options(
                    load_only('row_id')).all()
            if old_activities:
                old_activity_ids = [a.row_id for a in old_activities]
                reminders2 = Reminder.query.filter(Reminder.activity_id.in_(
                    old_activity_ids))
                if not dry:
                    reminders2.delete(synchronize_session=False)
                    db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
