"""
Models for "post comments" package.
"""

from app import db
from app.base.models import BaseModel
from app.resources.feeds.models import FeedItem


class PostComment(BaseModel):

    __tablename__ = 'post_comment'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='post_comment_account_id_fkey', ondelete='CASCADE'),
        nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='post_comment_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='post_comment_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)
    post_id = db.Column(db.BigInteger, db.ForeignKey(
        'post.id', name='post_comment_post_id_fkey', ondelete='CASCADE'),
        nullable=False)

    message = db.Column(db.String(1024), nullable=False)

    # incase this is a reply to another comment
    in_reply_to = db.Column(db.BigInteger, db.ForeignKey(
        'post_comment.id', name='post_comment_in_reply_to_fkey',
        ondelete='CASCADE'))

    edited = db.Column(db.Boolean, default=False)

    # relationships
    account = db.relationship('Account', backref=db.backref(
        'post_comments', lazy='dynamic'))
    creator = db.relationship('User', backref=db.backref(
        'post_comments', lazy='dynamic'),
        foreign_keys='PostComment.created_by')
    post = db.relationship('Post', backref=db.backref(
        'post_comments', lazy='dynamic'))
    # #TODO: may be used in future
    post_commented = db.relationship('PostComment', backref=db.backref(
        'post_comments', lazy='dynamic'), remote_side='PostComment.row_id')
    # special relationship for already commented eager loading check
    posts_j = db.relationship('Post', backref=db.backref(
        'post_commented', uselist=False))
    posts_f = db.relationship('FeedItem', backref=db.backref(
        'feed_commented', uselist=False),
        foreign_keys='[PostComment.post_id]',
        primaryjoin='PostComment.post_id == FeedItem.post_id')

    def __init__(self, *args, **kwargs):
        super(PostComment, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<PostComment %r>' % (self.message)
