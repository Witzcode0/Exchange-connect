import datetime

from flask_script import Command, Option
from sqlalchemy import func

from app import db
from app.resources.users.models import User
from app.resources.notifications.models import Notification


class UpdateUserNotificationsCount(Command):
    """
    Update the notification count for the users according to
    unread notifications.
    """
    option_list = [
        Option('--verbose', '-v', dest='verbose', action='store_true',
               default=False),
        Option('--dry', '-dry', dest='dry', action='store_true',
               default=False),
    ]

    def run(self, verbose, dry):
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('Updating notifications count ...')
        
        try:
            user_and_notification_counts = Notification.query.\
                with_entities(Notification.user_id, \
                    func.count(Notification.user_id)).group_by(
                    Notification.user_id).\
                filter_by(read_time = None).all()
            
            for user_id , notification_cnt in user_and_notification_counts:
                User.query.filter_by(row_id = user_id).update({
                    'current_notification_count': notification_cnt})
            
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
