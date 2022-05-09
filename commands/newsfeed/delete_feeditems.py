import datetime

from flask_script import Command, Option
from dateutil.relativedelta import relativedelta

from app import db
from app.resources.news.models import NewsItem


class DeleteFeedItems(Command):
    """
    Command to remove old feed items

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
            print('Removing old feed entries...')

        try:
            old_date = datetime.datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0) -\
                relativedelta(months=6)
            query = NewsItem.query.filter(
                NewsItem.posted_at < old_date)

            batch = 500
            cnt = 0
            for item in query.all():
                if not len(item.accounts):
                    cnt += 1
                    db.session.delete(item)
                    if cnt == batch:
                        db.session.commit()
                        cnt = 0
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
