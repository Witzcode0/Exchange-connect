"""
Models for "post stars" package.
"""

from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.resources.posts.models import Post
from app.resources.feeds.models import FeedItem


class PostStar(BaseModel):

    __tablename__ = 'post_star'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='post_star_account_id_fkey', ondelete='CASCADE'),
        nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='post_star_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='post_star_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)
    post_id = db.Column(db.BigInteger, db.ForeignKey(
        'post.id', name='post_star_post_id_fkey', ondelete='CASCADE'),
        nullable=False)

    # multi column
    __table_args__ = (
        UniqueConstraint('created_by', 'post_id',
                         name='c_created_by_post_id_key'),
    )

    # relationships
    account = db.relationship('Account', backref=db.backref(
        'post_stars', lazy='dynamic'))
    creator = db.relationship('User', backref=db.backref(
        'post_stars', lazy='dynamic'), foreign_keys='PostStar.created_by')
    post = db.relationship('Post', backref=db.backref(
        'post_stars', lazy='dynamic'))
    # special relationship for already starred eager loading check
    posts_j = db.relationship('Post', backref=db.backref(
        'post_starred', uselist=False))
    posts_f = db.relationship('FeedItem', backref=db.backref(
        'feed_starred', uselist=False),
        foreign_keys='[PostStar.post_id]',
        primaryjoin='PostStar.post_id == FeedItem.post_id')

    def __init__(self, post_id=None, stars=None, *args, **kwargs):
        self.post_id = post_id
        self.stars = stars
        super(PostStar, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<PostStar %r>' % (self.row_id)
