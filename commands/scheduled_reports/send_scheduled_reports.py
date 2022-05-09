import datetime
import requests

from dateutil.relativedelta import relativedelta
from flask_script import Command, Option
from config import SEND_REPORT_DOMAIN, REPORT_USER_EMAIL
from flask_jwt_extended import create_access_token

from app import db, flaskapp
from app.resources.scheduled_reports.models import (
    ScheduledReport, ScheduledReportLog)
from app.resources.scheduled_reports import constants as SCH_REPORT
from app.resources.users.models import User
from app.auth.schemas import UserIdentitySchema
from app.base import constants as CONST

from queueapp.tasks import send_email_actual


class SendScheduleReports(Command):
    """
    Command to send scheduled reports

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
        next_minute = curr_minute + datetime.timedelta(
            minutes=SCH_REPORT.CRON_TIME_INTERVAL)
        scheduled_reports = ScheduledReport.query.filter(
            ScheduledReport.is_active == True,
            ScheduledReport.deleted == False,
            ScheduledReport.end_date > next_minute,
            ScheduledReport.next_at < next_minute).all()
        reports_nr = len(scheduled_reports)
        report_and_logs = {}
        for report in scheduled_reports:
            log = ScheduledReportLog(
                report_id=report.row_id, status=SCH_REPORT.UNSENT,
                created_by=report.created_by, account_id=report.account_id)
            report_and_logs[report.row_id] = log

        db.session.add_all([v for k, v in report_and_logs.items()])
        db.session.commit()
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('Sending scheduled reports...')

        try:
            # creating access token
            user = User.query.filter_by(email=REPORT_USER_EMAIL).first()
            user.current_account = user.account
            identity_schema = UserIdentitySchema()
            result = identity_schema.dump(user)
            expires_delta = datetime.timedelta(days=1)
            token = 'Bearer ' + create_access_token(
                identity=result.data, expires_delta=expires_delta)

            headers = {
                'content-type': 'application/json',
                'Authorization': token
            }

            for each in scheduled_reports:
                try:
                    if (each.creator.report_downloaded + 1 >
                            each.creator.report_download_limit):
                        reports_nr -= 1
                        self.update_log(
                            "user report download limit reached",
                            [report_and_logs[each.row_id]])
                        continue
                    url = SEND_REPORT_DOMAIN + \
                        SCH_REPORT.SCH_REPORT_URLS[each.type]

                    json_data = {**each.request_body}
                    end_date = each.next_at.strftime("%Y-%m-%d")
                    start_date = each.next_at - relativedelta(years=1)
                    json_data['report_id'] = each.row_id
                    json_data['report_log_id'] = \
                        report_and_logs[each.row_id].row_id
                    json_data['allDetails']['endDate'] = end_date
                    json_data['allDetails']['selectedDate'] = end_date
                    json_data['allDetails']['startDate'] = \
                        start_date.strftime("%Y-%m-%d")

                    response = requests.post(
                        url, json=json_data, headers=headers, verify=False)
                    each.request_body = json_data
                    each.creator.report_downloaded += 1
                    db.session.add(each.creator)
                except Exception as e:
                    reports_nr -= 1
                    self.update_log(e, [report_and_logs[each.row_id]])
                finally:
                    while each.next_at < next_minute:
                        each.calculate_next_at()
                    db.session.add(each)
                    db.session.commit()

            print('sent {} out of {} reports'.format(
                reports_nr, len(scheduled_reports)))

        except Exception as e:
            print(e)
            if scheduled_reports:
                to_addresses = flaskapp.config['DEVELOPER_EMAILS']
                from_name = flaskapp.config['DEFAULT_SENDER_NAME']
                from_email = flaskapp.config['DEFAULT_SENDER_EMAIL']
                body = "failed scheduled report ids - {}.\
                Schedule report logs are saved in database".format(
                    ', '.join([str(each.row_id) for each in scheduled_reports]))
                send_email_actual(
                    subject="Exception occurred while sending research report",
                    keywords=CONST.SCHEDULE_REPORTS,
                    from_name=from_name,
                    from_email=from_email,
                    to_addresses=to_addresses, reply_to='', body=body,
                    html='', attachment='')
                self.update_log(e, [v for k, v in report_and_logs.items()])
                for each in scheduled_reports:
                    while each.next_at < next_minute:
                        each.calculate_next_at()
                    db.session.add(each)
                db.session.commit()
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')

    @staticmethod
    def update_log(e, logs):
        for log in logs:
            log.status = SCH_REPORT.UNSENT
            log.response_body = str(e)
            db.session.add(log)
        db.session.commit()
