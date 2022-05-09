import datetime

from flask_script import Command, Option

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
                datetime.timedelta(days=30)
            old_items = NewsItem.query.filter(NewsItem.posted_at < old_date)
            if not dry:
                old_items.delete(synchronize_session=False)
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
