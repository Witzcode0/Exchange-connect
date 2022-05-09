import datetime
import time

from flask_script import Command, Option
from sqlalchemy import desc
from sqlalchemy.orm import load_only
from flashtext import KeywordProcessor

from app import db
from app.resources.news.models import NewsItem
from app.resources.news import constants as NEWS


class TagNews(Command):

    option_list = [
        Option('--verbose', '-v', dest='verbose', action='store_true',
               default=False),
        Option('--dry', '-dry', dest='dry', action='store_true',
               default=False)
    ]

    def run(self, verbose, dry):
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('Tagging news ...')
        try:
            start_time = time.clock()
            start = 0
            batch = 500
            # all news items taken as a python list for the sake of
            # db performance
            news_cnt = NewsItem.query.count()
            news_items = list(db.session.query(NewsItem).options(
                load_only(
                    'row_id', 'title', 'description', 'tags',
                    'news_name')).order_by(desc(NewsItem.posted_at)).all())
            news_tags = {
                NEWS.NEWS_FIN: ['financial'],
                NEWS.NEWS_MARKET: ['markets'],
                NEWS.NEWS_BUSINESS: ['business'],
                NEWS.NEWS_ECON: ['economy', 'economic']
            }
            tag_processor = KeywordProcessor()
            tag_processor.add_keywords_from_dict(news_tags)

            news_batch = news_items[start: start+batch]
            commit_batch = 100
            commit_cnt = 0
            while news_batch:
                for news in news_batch:
                    found = tag_processor.extract_keywords(news.news_name)
                    if found:
                        tags = list(set(found))
                        news.tags = tags
                        db.session.add(news)
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
