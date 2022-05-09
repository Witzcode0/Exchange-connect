import datetime


from flask import current_app
from flask_script import Command, Option
from sqlalchemy import and_

from app import db
from app.resources.bse.models import BSEFeed
from app.resources.descriptor.models import BSE_Descriptor
from app.resources.corporate_announcements.models import CorporateAnnouncement
from app.common.helpers import time_converter

class Updatebseeccat(Command):
    """
    Command to update ec category from bse corp feed

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

        bsefeeds = BSEFeed.query.all()
        for each_feed in bsefeeds:
            # update feed ec_category - old data
            ec_cat = BSE_Descriptor.query.filter(BSE_Descriptor.descriptor_id == each_feed.descriptor_id).first()
            if ec_cat:
                ec_cat = ec_cat.category_id
            else:
                ec_cat = None
            if each_feed.scrip_cd is not None:
                try:
                    pass
                    BSEFeed.query.filter(BSEFeed.row_id == each_feed.row_id).update(
                        {BSEFeed.ec_category: ec_cat}, synchronize_session=False)
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    print(e)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')