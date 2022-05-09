import datetime
import time

from flask_script import Command, Option
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.orm import load_only
from flashtext import KeywordProcessor

from app import db
try:
    from config import NEWS_EXCLUDE_COMP_IDS
except ImportError:
    NEWS_EXCLUDE_COMP_IDS = []
from app.resources.accounts.models import Account
from app.resources.accounts import constants as ACC
from app.resources.news.models import NewsItem


class ImportAccountsNews(Command):

    option_list = [
        Option('--verbose', '-v', dest='verbose', action='store_true',
               default=False),
        Option('--dry', '-dry', dest='dry', action='store_true',
               default=False),
    ]

    def run(self, verbose, dry):
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('Updating account id of in caevents ...')
        try:
            start_time = time.clock()
            start = 0
            batch = 500
            accounts = db.session.query(Account).filter(and_(
                Account.deleted.is_(False),
                Account.account_type != ACC.ACCT_ADMIN)).options(
                load_only('row_id', 'account_name')).order_by(
                Account.account_name).all()
            if not accounts:
                exit(0)

            # account ids vs keyword lists, this dict will be holding keywords
            account_dict = {}
            # account id vs account instance
            account_and_instance  = {}
            for account in accounts:
                account_dict[account.row_id] = account.keywords
                account_and_instance[account.row_id] = account

            processor = KeywordProcessor()
            processor.add_keywords_from_dict(account_dict)
            # all news items taken as a python list for the sake of
            # db performance
            news_cnt = NewsItem.query.count()
            news_items = list(db.session.query(NewsItem).options(
                load_only('row_id', 'title', 'description')).order_by(desc(
                    NewsItem.posted_at)).all())
            news_batch = news_items[start: start+batch]
            commit_batch = 100
            commit_cnt = 0
            while news_batch:
                for news in news_batch:
                    found = processor.extract_keywords(
                        news.title + ' ' + news.description)
                    if found:
                        for account_id in set(found):
                            account = account_and_instance[account_id]
                            if account:
                                news.accounts.append(account)
                                commit_cnt += 1
                                if commit_cnt == commit_batch:
                                    db.session.commit()
                                    commit_cnt = 0
                start += batch
                news_batch = news_items[start: start+batch]
                print("processed {}/{}".format(start, news_cnt))
            db.session.commit()
            print("finished in {} seconds".format(time.clock() - start_time))
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')