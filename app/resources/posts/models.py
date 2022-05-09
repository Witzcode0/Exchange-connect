"""
Models for "posts" package.
"""

from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app import db
from app.base.models import BaseModel
from app.resources.post_file_library.models import PostLibraryFile
# ^ required for relationship


# association table for many-to-many post files
postfiles = db.Table(
    'postfiles',
    db.Column('post_id', db.BigInteger, db.ForeignKey(
        'post.id', name='postfiles_post_id_fkey', ondelete="CASCADE"),
        nullable=False),
    db.Column('file_id', db.BigInteger, db.ForeignKey(
        'post_library_file.id', name='postfiles_file_id_fkey',
        ondelete="CASCADE"), nullable=False),
    UniqueConstraint('post_id', 'file_id', name='ac_post_id_file_id_key'),
)


class Post(BaseModel):

    __tablename__ = 'post'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='post_account_id_fkey', ondelete='CASCADE'),
        nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='post_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='post_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)
    # post id which shared
    post_shared_id = db.Column(db.BigInteger, db.ForeignKey(
        'post.id', name='post_post_shared_id_fkey', ondelete='CASCADE'))

    title = db.Column(db.String(512))
    description = db.Column(db.String(9216))

    shared_url_preview = db.Column(JSONB)
    slug = db.Column(db.String(256))  # to link this post on shares

    edited = db.Column(db.Boolean, default=False)
    # post shared or not
    shared = db.Column(db.Boolean, default=False)

    # deleted bit
    deleted = db.Column(db.Boolean, default=False)

    # relationships
    account = db.relationship('Account', backref=db.backref(
        'posts', lazy='dynamic'))
    creator = db.relationship('User', backref=db.backref(
        'posts', lazy='dynamic'), foreign_keys='Post.created_by')
    editor = db.relationship('User', backref=db.backref(
        'updated_posts', lazy='dynamic'), foreign_keys='Post.updated_by')
    # linked files
    files = db.relationship(
        'PostLibraryFile', secondary=postfiles, backref=db.backref(
            'posts', lazy='dynamic'), passive_deletes=True)
    # shared post detail
    shared_post = db.relationship('Post', backref=db.backref(
        'posts', lazy='dynamic'), remote_side='Post.row_id')

    def __init__(self, *args, **kwargs):
        super(Post, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Post %r>' % (self.title)
