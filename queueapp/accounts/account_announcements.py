from app import db
from app.resources.accounts.models import Account
from app.resources.bse.models import BSEFeed
from app.resources.corporate_announcements.models import CorporateAnnouncement

from queueapp.tasks import celery_app, logger


@celery_app.task(bind=True, ignore_result=True)
def link_account_announcements(self, result, account_id, *args, **kwargs):
    """
    link account and bse feed announcements if not already
    """

    if result:
        try:
            account = Account.query.get(account_id)
            if not account:
                return False
            tagged_feeds = 0
            ident = account.identifier.split('-')[0]
            feeds = BSEFeed.query.filter_by(scrip_cd=ident)
            for each_feed in feeds:
                ca_feed = CorporateAnnouncement(
                    category=each_feed.exchange_category,
                    subject=each_feed.news_sub,
                    description=each_feed.news_body,
                    url=each_feed.attachment_url,
                    bse_type_of_announce=each_feed.type_of_announce,
                    source='bse_api',
                    account_id=account.row_id,
                    bse_descriptor=each_feed.descriptor_id,
                    announcement_date=each_feed.dt_tm,
                    created_by=account.created_by,
                    updated_by=account.updated_by)
                db.session.add(ca_feed)
                tagged_feeds += 1
            db.session.commit()
            print("Tagged {} bse announcements to account {}".format(
                tagged_feeds, account_id))

        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

        return result


@celery_app.task(bind=True, ignore_result=True)
def link_account_id(self, result, account_id, *args, **kwargs):

    if result:
        pass
        account = Account.query.get(account_id)
        if not account:
            return False
        tagged_feeds = 0
        ident = account.identifier.split('-')[0]
        feeds = BSEFeed.query.filter_by(scrip_cd=ident)
        for each_feed in feeds:
            try:
                BSEFeed.query.filter(BSEFeed.row_id == each_feed.row_id).update(
                    {BSEFeed.acc_id: account_id}, synchronize_session=False)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(e)