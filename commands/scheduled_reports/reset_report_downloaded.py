import datetime

from flask_script import Command, Option

from app import db
from app.resources.users.models import User


class ResetReportDownloaded(Command):
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
            print('resetting report downloaded...')

        try:
            User.query.update(
                {'report_downloaded': 0}, synchronize_session=False)
            db.session.commit()

        except Exception as e:
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')

