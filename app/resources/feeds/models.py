"""
Models for "feeds" package.
"""

from app import db
from app.base.models import BaseModel


class FeedItem(BaseModel):

    __tablename__ = 'feed_item'

    # the user who should see this feed
    user_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='feed_item_user_id_fkey', ondelete='CASCADE'),
        nullable=False)
    post_id = db.Column(db.BigInteger, db.ForeignKey(
        'post.id', name='feed_item_post_id_fkey', ondelete='CASCADE'),
        nullable=False)

    post_date = db.Column(db.DateTime, nullable=False)
    poster_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='feed_item_poster_id_fkey', ondelete='CASCADE'),
        nullable=False)

    # relationships
    # account = db.relationship('Account', backref=db.backref(
    #     'feeds', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref(
        'feeds', lazy='dynamic'), foreign_keys='FeedItem.user_id')
    post = db.relationship('Post', backref=db.backref(
        'feeds', lazy='dynamic'))

    def __init__(self, *args, **kwargs):
        super(FeedItem, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<FeedItem %r>' % (self.post_id)
