import datetime
import requests
import feedparser

from io import BytesIO

from flask import current_app
from flask_script import Command, Option
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from flashtext import KeywordProcessor
from sqlalchemy import and_
from sqlalchemy.orm import  load_only

from app import db
from app.resources.news.models import NewsSource, NewsItem
from app.resources.accounts.models import Account
from app.resources.accounts import constants as ACC
from app.resources.news import constants as NEWS
from app.base import constants as APP
from app import es

try:
    from config import NEWS_EXCLUDE_COMP_IDS
except ImportError:
    NEWS_EXCLUDE_COMP_IDS = []

from queueapp.tasks import send_email_task

def create_es_index(index):
    '''create index '''

    request_body = {
        "settings" : {
            "number_of_shards": 5,
            "number_of_replicas": 1
        },

        # 'mappings': {
        #     'doc': {
        #         'properties': {
        #             'news_id': {'type': 'string'},
        #             'news_name': {'type': 'string'},
        #             'domain_id': {'type': 'integer'},
        #             'news_date': {'type': 'date'}
        #         }}}
    }
    es.indices.create(index = index, body = request_body)

def update_es_index(index,data,id_news):
    '''add data in given index'''

    res = es.create(index = index, doc_type= index, id=id_news, body = data)

def search_index(index, title, domain_id, today_date, page=1, per_page=10):
    ''' search title in given index'''

    result = {
        'total': 0,
        'results': []
    }

    try:
        query = {
            "query":{
                "multi_match": {
                    "query": title,
                    "fields": [
                        "news_title"
                    ],
                    "minimum_should_match": "90%"
                }
            }
        }
        search = es.search(index=index, doc_type=index, body=query)
        result['total'] = search['hits']['total']

    except Exception as e:
        print(e)
        exit(0)
    return result

class FetchNews(Command):
    """
    Command to fetch news, and populate the newsfeed db

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
            print('Updating news ...')

        fs_url = ''  # helps with sending error email
        entry = ''  # helps with sending error email
        try:
            sources = NewsSource.query.all()
            if not sources or not len(sources):
                return
            # prepairing keywords
            accounts = db.session.query(Account).filter(and_(
                Account.deleted.is_(False),
                Account.account_type != ACC.ACCT_ADMIN)).options(
                load_only('row_id', 'account_name')).order_by(
                Account.account_name).all()
            news_tags = {
                NEWS.NEWS_FIN: ['financial'],
                NEWS.NEWS_MARKET: ['markets'],
                NEWS.NEWS_BUSINESS: ['business'],
                NEWS.NEWS_ECON: ['economy', 'economic']
            }
            account_dict = {}
            account_and_instance = {}
            for account in accounts:
                account_dict[account.row_id] = account.keywords
                account_and_instance[account.row_id] = account

            processor = KeywordProcessor()
            processor.add_keywords_from_dict(account_dict)
            cat_processor = KeywordProcessor()
            cat_processor.add_keywords_from_dict(news_tags)

            index = APP.NW_ES_INDEX
            if not es.indices.exists(index=index):
                create_es_index(index)

            for fsrc in sources:
                fs_url = fsrc.news_url
                resp = ''
                # fetch latest
                retries = 0  # try a few times
                fetched = False
                while retries < 3 and not fetched:
                    try:
                        resp = requests.get(fs_url, timeout=20.0)
                    except requests.ReadTimeout:
                        print("Timeout when reading RSS %s", fs_url)
                        retries += 1
                    else:
                        fetched = True
                if not fetched or not resp:
                    continue
                # update fetched time
                fsrc.last_fetched = datetime.datetime.utcnow()
                if not dry:
                    db.session.add(fsrc)
                    db.session.commit()

                # parse content through BytesIO stream
                feed = feedparser.parse(BytesIO(resp.content))

                if not feed.entries:
                    continue

                for entry in feed.entries:
                    # simple validate entry
                    try:
                        guid, title, link, posted_at, description, tags =\
                            NewsItem.parse_entry(entry)
                    except Exception as e:
                        print(e)
                        guid, title, link, posted_at, description = '', '',\
                            '', '', ''
                    if (not guid or not title or not link or not posted_at or
                            not description):
                        print('Failed to insert item = %s' % entry)
                        continue

                    # check duplicate using elasticsearch
                    today_date = datetime.date.today()
                    search_news = search_index(index,title,fsrc.domain_id,today_date)

                    if not search_news['total'] > 0:
                        try:
                            if "Moneycontrol" in fsrc.news_name:
                                title = title.replace("#39;", "'")
                                description = description.replace("#39;", "'")
                            if description == 'NULL':
                                description = ''
                            fitem = NewsItem(
                                guid=guid, title=title, link=link,
                                posted_at=posted_at, description=description,
                                tags=tags, news_name=fsrc.news_name,
                                news_url=fsrc.news_url, domain_id=fsrc.domain_id)

                            found = processor.extract_keywords(
                                fitem.title + ' ' + fitem.description)
                            if found:
                                for account_id in set(found):
                                    account = account_and_instance[account_id]
                                    if account:
                                        fitem.accounts.append(account)
                            found = cat_processor.extract_keywords(fitem.news_name)
                            if found:
                                tags = list(set(found))
                                fitem.tags = tags
                            fitem.parse_description()
                            if not dry:
                                db.session.add(fitem)
                                db.session.commit()
                                # add data into elasticsearch index
                                news = {}
                                news['news_id'] = fitem.row_id
                                news['news_title'] = title
                                news['news_domain'] = fsrc.domain_id
                                news['news_date'] = today_date
                                update_es_index(index,news,fitem.row_id)
                        except IntegrityError as e:
                            db.session.rollback()
                            continue

        except Exception as e:
            db.session.rollback()
            print(e)
            e = 'News update error:\r\n\r\n' + str(e) + '\r\n\r\n' +\
                'Src URL: ' + str(fs_url) + '\r\n\r\nEntry: ' + str(entry)
            # send_email_task.delay(email_type='error', e=e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')