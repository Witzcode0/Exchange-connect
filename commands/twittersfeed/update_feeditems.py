import datetime
import json
import dateutil
import re

from pytz import timezone
from flask_script import Command, Option
from sqlalchemy import func
from sqlalchemy.orm import load_only
from flask import current_app
from flashtext import KeywordProcessor

from app import db, tweepy_api
from app.resources.twitter_feeds.schemas import TwitterFeedSchema
from app.resources.twitter_feeds.models import TwitterFeeds, TwitterFeedSource
from app.resources.accounts.models import Account
from app.resources.accounts import constants as ACCT


class FetchTwitterFeed(Command):
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
            print('Updating twitter feed ...')

        try:
            # get max tweet id we have
            max_tweeter_id = db.session.query(
                func.max(TwitterFeeds.twitter_id)).first()[0]
            sources = {}
            all_twitter_sources = TwitterFeedSource.query.options(
                load_only('row_id', 'screen_name', 'last_tweet_id',
                          'domain_id')).all()
            for source in all_twitter_sources:
                sources[source.screen_name] = source
            account_keywords = {}
            account_and_instance = {}
            accounts = Account.query.filter(
                Account.account_type.notin_(
                    (ACCT.ACCT_ADMIN, ACCT.ACCT_GENERAL_INVESTOR))
            ).options(load_only('row_id', 'account_name')).all()
            for account in accounts:
                name = account.account_name.lower()
                keywords = list()
                if account.row_id not in current_app.config['TWITTER_EXCLUDE_AC_IDS']:
                    keyword = name.split(' ltd.')[0].split(
                        'co.')[0].split(' corp.')[0].replace('.', '')
                    keywords.append(keyword)
                    keywords.append('#' + keyword.replace(' ', ''))
                name = name.replace('.', '')
                keywords.append(name)
                keywords.append("#" + name.replace(" ", ""))
                account_keywords[account.row_id] = keywords
                account_and_instance[account.row_id] = account
            processor = KeywordProcessor()
            processor.add_keywords_from_dict(account_keywords)
            page = 1
            latest_tweet_id = None
            per_page = 200
            # OPTIMIZED maximum tweets we can get is 800 with pagination
            while True:
                all_tweets = tweepy_api.home_timeline(
                    count=per_page, page=page, since_id=max_tweeter_id,
                    max_id=latest_tweet_id, tweet_mode="extended")
                print("page {} - total tweets {} from {} to {}".format(
                    page, len(all_tweets), max_tweeter_id, latest_tweet_id))
                for tweet in all_tweets:
                    try:
                        tweet_data = {}
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
                            print(errors)
                            continue
                        data.tweet_date = tweet_date
                        tweet_source = sources[tweet_data['screen_name']]
                        data.domain_id = tweet_source.domain_id
                        matched_ac_ids = set(
                            processor.extract_keywords(tweet_data['text']))
                        if tweet_source.account:
                            data.accounts.append(tweet_source.account)
                            matched_ac_ids.discard(tweet_source.account.row_id)
                        for account_id in matched_ac_ids:
                            data.accounts.append(account_and_instance[account_id])
                        db.session.add(data)
                        db.session.commit()
                    except Exception as e:
                        print(e)
                        continue
                if not all_tweets:
                    break
                if not latest_tweet_id:
                    latest_tweet_id = all_tweets[0]['id']
                page += 1
        except Exception as e:
            print(e)
            exit(0)
