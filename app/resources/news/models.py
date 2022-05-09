"""
Models for "news" package.
"""

import requests
import feedparser
import dateutil
import pytz
import re

from io import BytesIO
from sqlalchemy import UniqueConstraint
from bs4 import BeautifulSoup

from app import db
from app.base.models import BaseModel
from app.resources.news import constants as NEWS

# association table for many-to-many news and accounts
newsaccounts = db.Table(
    'newsaccounts',
    db.Column('news_id', db.BigInteger, db.ForeignKey(
        'news_item.id', name='newsaccounts_news_id_fkey', ondelete="CASCADE"),
        nullable=False),
    db.Column('account_id', db.Integer, db.ForeignKey(
        'account.id', name='newsaccounts_account_id_fkey',
        ondelete="CASCADE"), nullable=False),
    UniqueConstraint('news_id', 'account_id', name='ac_news_id_account_id_key'),
)


class NewsSource(BaseModel):

    __tablename__ = 'news_source'

    news_name = db.Column(db.String(512), nullable=False)
    news_url = db.Column(db.String(1024), nullable=False, unique=True)
    domain_id = db.Column(db.BigInteger, db.ForeignKey(
        'domain.id', name='news_source_domain_id_fkey',
        ondelete='RESTRICT'), nullable=False)

    last_fetched = db.Column(db.DateTime)
    domain = db.relationship('Domain', backref=db.backref(
        'news_sources', uselist=True),
        primaryjoin='NewsSource.domain_id == Domain.row_id')

    def __init__(self, news_name=None, news_url=None, *args, **kwargs):
        self.news_name = news_name
        self.news_url = news_url
        super(NewsSource, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<NewsSource row_id=%r, news_name=%r, news_url=%r>' % (
            self.row_id, self.news_name, self.news_url)

    @classmethod
    def verify_source(cls, model, update_name=True):
        """
        Calls the feed url, and verifies if it is in expected format.

        :param update_name:
            whether to update the feed_name of the passed model
        """
        if not model:
            raise Exception('A model is required')

        resp = ''
        retries = 0  # try a few times
        fetched = False
        # fetch source
        while retries < 3 and not fetched:
            try:
                resp = requests.get(model.news_url, timeout=20.0)
            except requests.ReadTimeout:
                retries += 1
            else:
                fetched = True
        if not fetched or not resp:
            return False
        # parse content through BytesIO stream
        feed = feedparser.parse(BytesIO(resp.content))

        if not feed.entries:
            return False
        # verify format
        verified = NewsItem.parse_entry(feed.entries[0], return_values=False)

        if update_name:
            model.news_name = feed.feed.title

        return verified


class NewsItem(BaseModel):

    __tablename__ = 'news_item'

    guid = db.Column(db.String(1024), nullable=False, unique=True)
    title = db.Column(db.String(512), nullable=False)
    link = db.Column(db.String(1024), nullable=False)
    posted_at = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.String(), nullable=False)
    tags = db.Column(db.ARRAY(db.String), nullable=False)
    news_name = db.Column(db.String(512), nullable=False)
    news_url = db.Column(db.String(1024), nullable=False)
    domain_id = db.Column(db.BigInteger, db.ForeignKey(
        'domain.id', name='news_item_domain_id_fkey',
        ondelete='RESTRICT'), nullable=False)
    image_url = db.Column(db.String(1024))
    short_desc = db.Column(db.String())

    accounts = db.relationship(
        'Account', secondary=newsaccounts, backref=db.backref(
            'news', lazy='dynamic'), passive_deletes=True)
    domain = db.relationship('Domain', backref=db.backref(
        'news_items', uselist=True),
        primaryjoin='NewsItem.domain_id == Domain.row_id')

    def __init__(self, guid=None, title=None, link=None, posted_at=None,
                 description=None, tags=None, *args, **kwargs):
        self.guid = guid
        self.title = title
        self.link = link
        self.posted_at = posted_at
        self.description = description
        self.tags = tags
        super(NewsItem, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<NewsItem row_id=%r, guid=%r, title=%r, link=%r>' % (
            self.row_id, self.guid, self.title, self.link)

    def parse_description(self):
        soup = BeautifulSoup(self.description, 'html.parser')
        image = soup.find('img')
        self.short_desc = soup.text.strip()[:NEWS.SHORT_DESC_LENGTH]
        if image:
            self.image_url = image.get('src')

    @classmethod
    def parse_entry(cls, entry, return_values=True):
        """
        Parse a news entry.

        :param return_values:
            boolean indicating whether to simply return the values, if False
            it verifies that none of the expected values are empty, and returns
            None if any are empty, thereby validating it.
        """
        if not entry:
            raise Exception('A news entry is required')

        guid = ''
        if 'guid' in entry:
            guid = entry.guid
        title = ''
        if 'title' in entry:
            title = entry.title
        link = ''
        if 'link' in entry:
            link = entry.link
        posted_at = ''
        if 'published' in entry:
            posted_at = entry.published
        elif 'updated' in entry:
            posted_at = entry.updated
        tags = []
        match_str = ' '.join(NEWS.NTAGS_TYPES)
        if 'tags' in entry:
            tags = [t.term for t in entry.tags if re.search(
                t.term.lower(), match_str)]
        # hack for some sites that give incorrect day names
        if 'Wes' in posted_at:
            posted_at = posted_at.replace('Wes', 'Wed')
        posted_at = dateutil.parser.parse(posted_at).astimezone(pytz.UTC)
        description = ''
        if 'description' in entry:
            description = entry.description
        elif 'summary' in entry:
            description = entry.summary

        if return_values:
            return guid, title, link, posted_at, description, tags

        if (not guid or not title or not link or not posted_at or
                not description):
            return None
        else:
            return True


class TopNews(BaseModel):

    __tablename__ = 'top_news'

    date = db.Column(db.Date, nullable=False)
    news_ids = db.Column(db.ARRAY(db.BigInteger, db.ForeignKey(
        'news_items.id', ondelete='CASCADE')), nullable=False)
    domain_id = db.Column(db.BigInteger, db.ForeignKey(
        'domain.id', name='top_news_domain_id_fkey',
        ondelete='CASCADE'), nullable=False)

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='news_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='news_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)

    def __init__(self, date=None, *args, **kwargs):
        self.date = date
        super(TopNews, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<TopNews date=%r>' % (
            self.date)
