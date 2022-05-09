import datetime

from flask_script import Command, Option

from app.resources.scheduled_reports.models import ScheduledReport


class DeactivateScheduleReports(Command):
    """
    Command to inactive scheduled reports having end date less than
    current time

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

        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('deactivating scheduled reports...')

        try:
            curr_time = datetime.datetime.utcnow()
            scheduled_reports = ScheduledReport.query.filter(
                ScheduledReport.is_active == True,
                ScheduledReport.deleted == False,
                ScheduledReport.end_date < curr_time).update(
                {'is_active': False}, synchronize_session=False)
            print("deactivated {} scheduled reports".format(scheduled_reports))

        except Exception as e:
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')

