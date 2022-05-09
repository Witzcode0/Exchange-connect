"""
Feed related tasks, for each type of feed
"""

from app import db

from sqlalchemy import or_, and_
from sqlalchemy.orm import load_only

from queueapp.tasks import celery_app, logger
from app.resources.posts.models import Post
from app.resources.contacts.models import Contact
from app.resources.feeds.models import FeedItem


@celery_app.task(bind=True, ignore_result=True)
def add_post_feed(self, result, row_id, *args, **kwargs):
    """
    Adds a feed item for a post.
    Checks all contacts of post user, and adds post feed item for them.

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the post
    """

    if result:
        try:
            post_data = Post.query.get(row_id)
            if not post_data:
                return True

            # add feed for post created user
            db.session.add(FeedItem(
                user_id=post_data.created_by,
                post_id=row_id,
                post_date=post_data.created_date,
                poster_id=post_data.created_by))

            full_contact_data = Contact.query.filter(
                or_(Contact.sent_by == post_data.created_by,
                    Contact.sent_to == post_data.created_by)).options(
                        load_only('sent_by', 'sent_to')).all()

            # add feed for user contact
            if full_contact_data:
                for contact_data in full_contact_data:
                    if post_data.created_by == contact_data.sent_by:
                        db.session.add(FeedItem(
                            user_id=contact_data.sent_to,
                            post_id=row_id,
                            post_date=post_data.created_date,
                            poster_id=contact_data.sent_by))
                    elif post_data.created_by == contact_data.sent_to:
                        db.session.add(FeedItem(
                            user_id=contact_data.sent_by,
                            post_id=row_id,
                            post_date=post_data.created_date,
                            poster_id=contact_data.sent_to))
            db.session.commit()
            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def add_feed_for_new_contacts(self, result, contact_id, *args, **kwargs):
    """
    When new contact create then feed generate for sender and sendee

    :param contact_id: row_id id of contact
    """
    if result:
        try:
            count = 0
            batch_size = 100
            sendee_posts = None
            sender_posts = None
            contact_data = Contact.query.filter(
                Contact.row_id == contact_id).options(load_only(
                    'sent_to', 'sent_by', 'created_date')).first()

            if not contact_data:
                return True
            sender_posts = Post.query.filter(and_(
                Post.created_by == contact_data.sent_to,
                Post.deleted.is_(False))).all()
            sendee_posts = Post.query.filter(and_(
                Post.created_by == contact_data.sent_by,
                Post.deleted.is_(False))).all()

            # feed generate for sendee
            if sender_posts:
                for post in sender_posts:
                    count += 1
                    db.session.add(FeedItem(
                        user_id=contact_data.sent_by, post_id=post.row_id,
                        post_date=post.created_date,
                        poster_id=contact_data.sent_to))
                    if count >= batch_size:
                        db.session.commit()
                        count = 0
                if count:
                    db.session.commit()
                    count = 0
            # feed generate for sender
            if sendee_posts:
                for post in sendee_posts:
                    count += 1
                    db.session.add(FeedItem(
                        user_id=contact_data.sent_to, post_id=post.row_id,
                        post_date=post.created_date,
                        poster_id=contact_data.sent_by))
                    if count >= batch_size:
                        db.session.commit()
                        count = 0
                if count:
                    db.session.commit()

            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result
