import datetime

from flask_script import Command, Option
from sqlalchemy.orm import load_only
from sqlalchemy import and_

from app import db
from app.resources.contacts.models import Contact
from app.resources.posts.models import Post
from app.resources.feeds.models import FeedItem


class AddFeedPostHistory(Command):
    """
    Add post history in feed and update according to new Contacts
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
            print('Adding feeds ...')
        try:
            count = 0
            batch_size = 100
            sendee_posts = None
            sender_posts = None
            all_contacts = Contact.query.all()
            for contact in all_contacts:
                sendee_posts = Post.query.filter(and_(
                    Post.created_by == contact.sent_to,
                    Post.deleted.is_(False),
                    Post.created_date <= contact.created_date)).options(
                    load_only('row_id', 'created_date')).all()
                sender_posts = Post.query.filter(and_(
                    Post.created_by == contact.sent_by,
                    Post.deleted.is_(False),
                    Post.created_date <= contact.created_date)).options(
                    load_only('row_id', 'created_date')).all()
                # feed generate for sendee
                if sender_posts:
                    for post in sender_posts:
                        feed = None
                        feed = FeedItem.query.filter(
                            and_(FeedItem.post_id == post.row_id,
                                 FeedItem.user_id == contact.sent_to)).first()
                        if feed:
                            continue
                        count += 1
                        db.session.add(FeedItem(
                            user_id=contact.sent_to, post_id=post.row_id,
                            post_date=post.created_date,
                            poster_id=contact.sent_by))
                        if count >= batch_size:
                            db.session.commit()
                            count = 0
                    if count:
                        db.session.commit()
                        count = 0
                # feed generate for sender
                if sendee_posts:
                    for post in sendee_posts:
                        feed = None
                        feed = FeedItem.query.filter(
                            and_(FeedItem.post_id == post.row_id,
                                 FeedItem.user_id == contact.sent_by)).first()
                        if feed:
                            continue
                        count += 1
                        db.session.add(FeedItem(
                            user_id=contact.sent_by, post_id=post.row_id,
                            post_date=post.created_date,
                            poster_id=contact.sent_to))
                        if count >= batch_size:
                            db.session.commit()
                            count = 0
                    if count:
                        db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
