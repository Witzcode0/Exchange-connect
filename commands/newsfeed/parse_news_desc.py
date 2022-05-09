import datetime

from flask_script import Command, Option

from app import db
from app.resources.news.models import NewsItem


class ParseNewsDesc(Command):
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
            items = NewsItem.query.order_by(NewsItem.row_id)
            print('records to process {}'.format(items.count()))
            start = 0
            batch = 1000
            while True:
                news_batch = items.offset(start).limit(batch).all()
                if not news_batch:
                    break
                for item in news_batch:
                    item.parse_description()
                    db.session.add(item)
                db.session.commit()
                start += batch
                print('processed {} items'.format(start))
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')