import datetime
from sqlalchemy import func
from flask_script import Command, Option

from app import db
from app.resources.bse.models import BSEFeed
from app.resources.bse_mf_etf.models import BSEMFETFFeed
from app.resources.bse_mf_etf.schemas import BseMfEtfSchema


class MigrateMfEtf(Command):
    """
    Command to migrate mutual fund and etf data from bse to mf_etf model

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

        max_id = db.session.query(func.max(BSEFeed.row_id)).scalar()

        flag = True
        lim = 500
        off = 0
        MT_ETF_DESCRIPTORS = [18, 199, 200]

        while flag:
            #52817
            bsefeeds = BSEFeed.query.filter(BSEFeed.row_id > off).order_by(BSEFeed.row_id.asc()).limit(lim)
            if off != max_id:
                cnt = 0
                mcnt = 0
                try:
                    for each in bsefeeds:
                        cnt += 1
                        if any(x == each.descriptor_id for x in MT_ETF_DESCRIPTORS):
                            print(each.row_id)
                            db.session.add(BSEMFETFFeed(
                                scrip_cd=each.scrip_cd,
                                company_name = each.company_name,
                                dt_tm = each.dt_tm,
                                file_status = each.file_status,
                                head_line = each.head_line,
                                news_sub = each.news_sub,
                                attachment_name = each.attachment_name,
                                news_body = each.news_body,
                                descriptor = each.descriptor,
                                critical_news = each.critical_news,
                                type_of_announce = each.type_of_announce,
                                type_of_meeting = each.type_of_meeting,
                                date_of_meeting = each.date_of_meeting,
                                descriptor_id = each.descriptor_id,
                                attachment_url = each.attachment_name,
                                trade_date = each.trade_date
                            ))

                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    print(e)
                off = bsefeeds[-1].row_id
                print("last id is :",off)

            else:
                print("feeds over")
                flag = False
                break

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
