"""
Users Stats related tasks
"""

from app import db
from app.resources.twitter_feeds.models import TwitterFeedSource

from queueapp.tasks import celery_app, logger


@celery_app.task(bind=True, ignore_result=True)
def fetch_tweets(self, result, source_id, *args, **kwargs):
    """
    fetch tweets of a tweet source

    :param source:
        Object of TwitterFeedSource
    """

    if result:
        try:
            source = TwitterFeedSource.query.get(source_id)
            if source:
                source.fetch_tweets()
                result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

        return result
