import datetime
from flask_script import Command, Option
from sqlalchemy import and_
from sqlalchemy.orm import load_only

from app import db
from app.resources.corporate_announcements.models import CorporateAnnouncement
from app.resources.descriptor.models import BSE_Descriptor
from app.common.helpers import time_converter


class UpdateCACategory(Command):
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

        category_df = {"news": 7,
                       "concall transcripts": 2,
                       "others": 8,
                       "result updates": 11,
                       "presentation": 11,
                       "annual reports": 1}
        feeds = db.session.query(CorporateAnnouncement).all()

        # feednew = CorporateAnnouncement.query.filter(and_(CorporateAnnouncement.category_id == None),
        #                          CorporateAnnouncement.source == 'bse_api').all()
        # print(feednew[0])
        # exit(0)
        for each_feed in feeds:
            if each_feed.bse_descriptor:
                cat_id = BSE_Descriptor.query.filter(BSE_Descriptor.descriptor_id ==
                            each_feed.bse_descriptor).options(load_only('category_id')).first()
                try:
                    CorporateAnnouncement.query.filter(CorporateAnnouncement.row_id == each_feed.row_id).update(
                        {CorporateAnnouncement.category_id: cat_id}, synchronize_session=False)
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    print(e)
                # each_feed.category_id = cat_id
            #and not each_feed.source
            elif each_feed.category:
                cat_id = category_df[each_feed.category]
                try:
                    CorporateAnnouncement.query.filter(CorporateAnnouncement.row_id == each_feed.row_id).update(
                        {CorporateAnnouncement.category_id: cat_id}, synchronize_session=False)
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    print(e)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
