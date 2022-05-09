import datetime
import pytz
import os
import shutil

from app import flaskapp, db, sockio
from flask_script import Command, Option
from sqlalchemy.orm import joinedload

from app import db
from app.activity.activities import constants as ACTIVITY
from app.resources.reminders import constants as REMINDER
from app.resources.reminders.models import Reminder


from app.activity.activities.models import Activity
from app.resources.activity_type.models import ActivityType
from app.resources.user_profiles.models import UserProfile
from app.resources.users import constants as USER
from app.common.helpers import generate_ics_file
from app.resources.notifications import constants as NOTIFY
from app.resources.notifications.schemas import NotificationSchema
from socketapp.base import constants as SOCKETAPP

from queueapp.tasks import celery_app, logger, send_email_actual

# from queueapp.reminder_tasks import (
#     send_email_reminder, send_notification_reminder)


def send_email_reminder(result, activity_id, *args, **kwargs):
    """
    Send an email reminder
    #TODO: will change in next iteration, for now adding format here.

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param activity_id:
        the activity id
    """
    if result:
        try:
            activity = Activity.query.options(joinedload(
                Activity.user)).get(activity_id)
            activity_type = ActivityType.query.filter_by(row_id=activity.activity_type).first()

            to_addresses = [activity.user.email]
            from_name = flaskapp.config['DEFAULT_SENDER_NAME']
            from_email = flaskapp.config['DEFAULT_SENDER_EMAIL']
            reply_to = ''
            subject = 'ExchangeConnect - Reminder for ' + activity_type.activity_name
            html = ''
            attachment = ''

            body = 'Hi %(user_name)s,' +'\n'+\
                'This is a reminder for  %(activity_type)s.' +'\n'+\
                'The details of %(activity_type)s are as following:' +'\n'+\
                'Time: %(time)s' +'\n'+\
                'Date: %(date)s' +'\n'+\
                'Agenda: %(agenda)s' +'\n'+\
                '\n\n'+\
                'Please log in to ExchangeConnect to attend %(activity_type)s.' +'\n'+\
                'Thanks.'
            tz = USER.DEF_TIMEZONE
            started_at = pytz.utc.localize(
                    activity.started_at, is_dst=None).astimezone(pytz.timezone(
                        tz))
            ended_at = None
            if activity.ended_at:
                ended_at = pytz.utc.localize(
                    activity.ended_at, is_dst=None).astimezone(pytz.timezone(
                        tz))
            user_profile = UserProfile.query.filter_by(user_id=activity.user.row_id).first()

            replace_dict = {
                'user_name': user_profile.first_name,
                'activity_type': activity_type.activity_name,
                'date':started_at.date(),
                'time':str(started_at.time().hour)+':'+str(started_at.time().minute)+':'+str(started_at.time().second),
                'started_at': started_at.strftime('%I:%M %p, %d, %b %Y'),
                'agenda': activity.agenda
            }
            # if activity.participants:
            #     body += '\r\n\r\nHere are the people involved: \r\n\r\n' +\
            #         '%(participants)s.'
            #     user_profiles_objs = [UserProfile.query.filter_by(user_id=i.row_id).first() for i in activity.participants] 
            #     replace_dict['participants'] = ', '.join([
            #         p.first_name + ' ' + p.last_name
            #         for p in user_profiles_objs])
            # body += '\r\n\r\nThanks.'

            subject = subject % replace_dict
            body = body % replace_dict
            ics_file = generate_ics_file(
                subject, started_at, activity_type.activity_name, ended_at)
            # send user email
            send_email_actual(
                subject=subject, from_name=from_name, from_email=from_email,
                to_addresses=to_addresses, reply_to=reply_to, body=body,
                html=html, attachment=attachment, ics_file=ics_file)
            if ics_file:
                # removing icsfile containing folder
                shutil.rmtree(os.path.dirname(ics_file))
            result = True
        except Exception as e:
            logger.exception(e)
            result = False

    return result

def send_notification_reminder(result, activity_id, *args, **kwargs):
    """
    Send the notification reminder

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param activity_id:
        the activity id
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            activity = Activity.query.options(joinedload(
                Activity.user)).get(activity_id)

            if not activity:
                return True

            user_profile = UserProfile.query.filter_by(user_id=activity.user.row_id).first()

            message_name['first_name'] = user_profile.first_name
            message_name['last_name'] = user_profile.last_name

            json_data['user_id'] = activity.created_by
            json_data['account_id'] = activity.user.account_id
            json_data['notification_type'] = NOTIFY.NT_AC_RM
            json_data['notification_group'] = NOTIFY.NG_AC_RM
            json_data['activity_id'] = activity_id

            data, errors = NotificationSchema().load(json_data)
            if errors:
                return True
            db.session.add(data)
            db.session.commit()

            # emit notification to user
            notify_user = activity.user
            notify_user.current_notification_count += 1
            db.session.add(notify_user)
            db.session.commit()
            sockio.emit('new_notification', {
                    'user_id': data.user_id,
                    'notification_row_id': data.row_id,
                    'notification_type': NOTIFY.NT_AC_RM},
                namespace=SOCKETAPP.NS_NOTIFICATION,
                room=notify_user.get_room_id(
                    room_type=SOCKETAPP.NS_NOTIFICATION))

            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result

class UpdateAndNotifyReminder(Command):
    """
    Command to maintain the reminder table, run once a minute, update next_at
    generate the notification (email or system)

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
        curr_minute = curr_time.replace(second=0, microsecond=0)
        next_minute = curr_minute + datetime.timedelta(minutes=5)
        if verbose:
            print('---' + str(curr_time) + '---')
            print('Updating reminders, and sending notifications/emails...'
                  'for minute ' + str(curr_minute))

        try:
            reminders = Reminder.query.filter(
                Reminder.next_at < next_minute,
                Reminder.next_at >= curr_minute).options(joinedload(
                    Reminder.activity), joinedload(Reminder.user)).all()
            expired_list = []
            for reminder in reminders:
                if (reminder.activity.started_at and
                        reminder.activity.started_at > curr_minute):
                    if reminder.reminder_sys_type == REMINDER.RST_DEFAULT:
                        send_email_reminder(
                            True, reminder.activity.row_id)
                        send_notification_reminder(
                            True, reminder.activity.row_id)
                    else:
                        if reminder.activity.reminder_type == ACTIVITY.RMT_EM:
                            send_email_reminder(
                                True, reminder.activity.row_id)
                        elif (reminder.activity.reminder_type ==
                                ACTIVITY.RMT_NO):
                            send_notification_reminder(
                                True, reminder.activity.row_id)

                else:
                    expired_list.append(reminder.row_id)

            # delete expired list
            if expired_list:
                expired = Reminder.query.filter(
                    Reminder.row_id.in_(expired_list))
                if not dry:
                    expired.delete(synchronize_session=False)
                    db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
