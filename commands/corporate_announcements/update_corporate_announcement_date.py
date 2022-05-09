import datetime
from flask_script import Command, Option
from sqlalchemy import and_

from app import db
from app.resources.corporate_announcements.models import CorporateAnnouncement
from app.common.helpers import time_converter

class Updatecadate(Command):
    """
    Command to update date from corporate announcements

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
            print('updating corporate announcement date...')

        start = '2021-08-17'
        end = '2021-08-23'

        # cafeeds = db.session.query(CorporateAnnouncement).all()
        cafeeds = CorporateAnnouncement.query.filter(and_
                                 (CorporateAnnouncement.announcement_date.between(start, end)),
                                 CorporateAnnouncement.source == 'bse_api')

        import pdb
        pdb.set_trace()
        for each_ca_feed in cafeeds:
            # update corporate announcements before 24th aug
            date = time_converter(each_ca_feed.announcement_date, 'UTC', 'Asia/Kolkata')
            if each_ca_feed.account_id is not None:
                try:
                    CorporateAnnouncement.query.filter(CorporateAnnouncement.row_id == each_ca_feed.row_id).update(
                        {CorporateAnnouncement.announcement_date: date}, synchronize_session=False)
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    print(e)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')