"""
account stats related tasks
"""

from sqlalchemy import and_, desc
from sqlalchemy.orm import load_only
from flashtext import KeywordProcessor

from app import db
from app.resources.accounts.models import Account
from app.resources.news.models import NewsItem

from queueapp.tasks import celery_app, logger


@celery_app.task(bind=True, ignore_result=True)
def link_account_news(self, result, account_id, *args, **kwargs):
    """
    link account and news if not already
    """

    if result:
        try:
            start = 0
            batch = 500
            account = Account.query.get(account_id)
            if not account:
                return False

            processor = KeywordProcessor()
            processor.add_keywords_from_list(account.keywords)
            news_items = list(db.session.query(NewsItem).options(
                load_only('row_id', 'title', 'description')).order_by(desc(
                NewsItem.row_id)).all())
            commit_batch = 100
            commit_cnt = 0
            newly_linked = 0
            while news_items[start: start + batch]:
                for news in news_items[start: start + batch]:
                    found = processor.extract_keywords(
                        news.title + ' ' + news.description)
                    if found and account not in news.accounts:
                        news.accounts.append(account)
                        commit_cnt += 1
                        newly_linked += 1
                        if commit_cnt == commit_batch:
                            db.session.commit()
                            commit_cnt = 0
                start += batch
            db.session.commit()
            print("linked {} new news for account {}".format(
                newly_linked, account_id))
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

        return result
