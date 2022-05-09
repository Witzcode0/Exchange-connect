import datetime
from flask_script import Command, Option
from sqlalchemy import and_

from app import db
from app.resources.bse.models import BSEFeed
from app.resources.corporate_announcements.models import CorporateAnnouncement
from app.common.helpers import time_converter


class UpdateBseDate(Command):
    """
    Command to update date from bse table and corporate announcements

    :arg verbose:        print progress
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
            print('updating bse corp feed date in utc format...')

        start = '2021-08-17'
        end = '2021-08-24'

        # feeds = db.session.query(BSEFeed).all()
        feeds = BSEFeed.query.filter(BSEFeed.dt_tm.between(start, end))
        for each_feed in feeds:
            # update feed datetime before 24th aug
            date = time_converter(each_feed.dt_tm, 'UTC', 'Asia/Kolkata')
            if each_feed.scrip_cd is not None:
                try:
                    BSEFeed.query.filter(BSEFeed.row_id == each_feed.row_id).update(
                        {BSEFeed.dt_tm: date}, synchronize_session=False)
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    print(e)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
