"""
Models for "twitter feed" package.
"""
import json
import dateutil
import re

from pytz import timezone
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import UniqueConstraint, func
from flask import current_app

from app import db, tweepy_api
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString, CastingArray


# association table for many-to-many tweets and accounts
tweetaccounts = db.Table(
    'tweetaccounts',
    db.Column('tweet_id', db.BigInteger, db.ForeignKey(
        'twitter_feed.id', name='tweetaccounts_tweet_id_fkey',
        ondelete="CASCADE"), nullable=False),
    db.Column('account_id', db.Integer, db.ForeignKey(
        'account.id', name='tweetaccounts_account_id_fkey',
        ondelete="CASCADE"), nullable=False),
    UniqueConstraint('tweet_id', 'account_id',
                     name='ac_tweet_id_account_id_key'),
)


class TwitterFeedSource(BaseModel):

    __tablename__ = 'twitter_source'

    account_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    screen_name = db.Column(db.String(1024), nullable=False, unique=True, )
    twitter_user_id = db.Column(db.String(1024), nullable=False, unique=True)
    full_name = db.Column(db.String(1024))
    last_tweet_id = db.Column(db.String(1024))
    domain_id = db.Column(db.BigInteger, db.ForeignKey(
        'domain.id', name='twitter_source_domain_id_fkey',
        ondelete='RESTRICT'), nullable=False)

    # relationships
    account = db.relationship('Account', backref=db.backref(
        'tweet_source', uselist=False))
    domain = db.relationship('Domain', backref=db.backref(
        'twitter_sources', uselist=True),
        primaryjoin='TwitterFeedSource.domain_id == Domain.row_id')

    def __init__(self, screen_name=None, *args, **kwargs):
        self.screen_name = screen_name
        super(TwitterFeedSource, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<TwitterFeedSource %r>' % self.screen_name

    def verify_user(self):
        try:
            twitter_user = tweepy_api.get_user(
                screen_name=self.screen_name)
            self.twitter_user_id = twitter_user['id_str']
            self.full_name = twitter_user['name']
            return True
        except Exception:
            return False

    def follow_source(self):
        try:
            twitter_user = tweepy_api.create_friendship(
                screen_name=self.screen_name)
            return True
        except Exception:
            return False

    def unfollow_source(self):
        try:
            twitter_user = tweepy_api.destroy_friendship(
                screen_name=self.screen_name)
            return True
        except Exception:
            return False

    def fetch_tweets(self):
        all_tweets = tweepy_api.user_timeline(
            screen_name=self.screen_name, count=1000,
            since_id=self.last_tweet_id, include_rts=True,
            exclude_replies=True, tweet_mode="extended")
        tweet_data = {}
        from app.resources.twitter_feeds.schemas import TwitterFeedSchema
        for tweet in all_tweets:
            try:
                json_data = json.loads(json.dumps(tweet))
                tweet_data['twitter_id'] = str(json_data['id'])
                tweet_data['twitter_user_id'] = str(
                    json_data['user']['id'])
                tweet_data['screen_name'] = json_data['user'][
                    'screen_name']
                tweet_data['full_name'] = json_data['user']['name']
                tweet_data['user_description'] = json_data['user'][
                    'description']
                tweet_data['profile_image_url'] = json_data['user'][
                    'profile_image_url_https']
                tweet_data['profile_background_image_url'] = json_data[
                    'user']['profile_background_image_url_https']
                tweet_data['text'] = json_data['full_text']
                tweet_data['feed_url'] = ''
                if ('urls' in json_data['entities'] and
                        json_data['entities']['urls']):
                    tweet_data['feed_url'] = json_data['entities'][
                        'urls'][0]['url']
                    tweet_data['expanded_url'] = json_data['entities'][
                        'urls'][0]['expanded_url']
                    tweet_data['hashtags'] = json_data['entities'][
                        'hashtags']
                urls = re.findall(
                    r'(https?://\S+)', tweet_data['text'])
                if urls:
                    tweet_data['tweet_url'] = urls[-1]
                tz = timezone('UTC')
                tweet_date = dateutil.parser.parse(
                    json_data['created_at']).astimezone(tz)
                data, errors = TwitterFeedSchema().load(tweet_data)
                if errors:
                    continue
                data.tweet_date = tweet_date
                db.session.add(data)
                db.session.commit()
            except Exception as e:
                current_app.logger.exception(e)
                continue
            last_tweet = db.session.query(
                func.max(TwitterFeeds.twitter_id).label(
                    'last_tweet_id')).filter(
                TwitterFeeds.screen_name == self.screen_name
            ).first()
            self.last_tweet_id = last_tweet.last_tweet_id
            db.session.commit()


class TwitterFeeds(BaseModel):

    __tablename__ = 'twitter_feed'

    twitter_id = db.Column(db.String(1024), nullable=False, unique=True)
    twitter_user_id = db.Column(db.String(1024))
    screen_name = db.Column(db.String(1024))
    full_name = db.Column(db.String(1024))
    user_description = db.Column(db.String(1024))
    profile_image_url = db.Column(db.String)
    profile_background_image_url = db.Column(db.String)

    text = db.Column(db.String)
    feed_url = db.Column(db.String)
    tweet_url = db.Column(db.String)
    expanded_url = db.Column(db.String)
    hashtags = db.Column(CastingArray(JSONB))
    tweet_date = db.Column(db.DateTime)
    domain_id = db.Column(db.BigInteger, db.ForeignKey(
        'domain.id', name='twitter_feed_domain_id_fkey',
        ondelete='RESTRICT'), nullable=False)

    accounts = db.relationship(
        'Account', secondary=tweetaccounts, backref=db.backref(
            'tweets', lazy='dynamic'), passive_deletes=True)
    domain = db.relationship('Domain', backref=db.backref(
        'tweets', uselist=True),
        primaryjoin='TwitterFeeds.domain_id == Domain.row_id')

    def __init__(self, screen_name=None, tweet_date=None, *args, **kwargs):
        self.screen_name = screen_name
        self.tweet_date = tweet_date
        super(TwitterFeeds, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<TwitterFeeds %r>' % self.screen_name

