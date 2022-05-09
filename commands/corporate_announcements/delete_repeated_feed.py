import datetime
from flask_script import Command, Option
from sqlalchemy import and_, func
from urllib.parse import urlparse, parse_qsl, unquote_plus

from app import db
from app.resources.bse.models import BSEFeed #bsefeedaccounts
from app.resources.corporate_announcements.models import CorporateAnnouncement
from app.common.helpers import time_converter


class DeleteRepeatedFeed(Command):
    """
    Command to fetch bse feed from db and delete repeatation of feed

    :arg verbose: print progress
    :arg dry:
        dry run
    """

    option_list = [
        Option('--verbose', '-v', dest='verbose', action='store_true',
               default=False),
        Option('--dry', '-dry', dest='dry', action='store_true',
               default=False),
    ]

    # from urllib.parse import urlparse, parse_qsl, unquote_plus

    def run(self, verbose, dry):
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('removing bse repetition ...')

        start = '2021-08-18'
        end = '2021-08-19'
        # end = '2021-08-24'

        cafeeds = CorporateAnnouncement.query.filter(and_(
                    CorporateAnnouncement.announcement_date.between(start, end),
                    CorporateAnnouncement.source == 'bse_api')).order_by(CorporateAnnouncement.url)

        allurl = []
        for each_ca_feed in cafeeds:
            allurl.append(each_ca_feed.url)

        unique_urls = list(set(allurl))
        try:
            for each_url in unique_urls:
                cnt = 0
                for each in cafeeds:
                    if each_url == each.url:
                        cnt += 1
                        if cnt > 1:
                            try:
                                db.session.delete(each)
                            except Exception as e:
                                print(e)
                                continue
                    else:
                        cnt = 0
                        continue
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
