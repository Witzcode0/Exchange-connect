"""
Models for "newswire posts" package.
"""

from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY

from app import db
from app.base.models import BaseModel
# related model imports done in newswires/__init__


# association table for many-to-many newswire post files
newswirepostfiles = db.Table(
    'newswirepostfiles',
    db.Column('newswire_post_id', db.BigInteger, db.ForeignKey(
        'newswire_post.id', name='newswirepostfiles_newswire_post_id_fkey',
        ondelete='CASCADE'), nullable=False),
    db.Column('newswire_file_id', db.BigInteger, db.ForeignKey(
        'newswire_post_library_file.id',
        name='newswirepostfiles_newswire_file_id_fkey', ondelete='CASCADE'),
        nullable=False),
    UniqueConstraint(
        'newswire_post_id', 'newswire_file_id',
        name='ac_newswire_post_id_newswire_file_id_key'),
)


class NewswirePost(BaseModel):

    __tablename__ = 'newswire_post'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='newswire_post_account_id_fkey',
        ondelete='CASCADE'), nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='newswire_post_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='newswire_post_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)

    company_name = db.Column(db.String(256))
    logo_file_id = db.Column(db.BigInteger, db.ForeignKey(
        'newswire_post_library_file.id',
        name='newswire_post_logo_file_id_fkey'))
    heading = db.Column(db.String(256))
    sub_heading = db.Column(db.String(512))
    body_text = db.Column(db.String(2048))
    link = db.Column(db.String(256))
    platforms = db.Column(ARRAY(db.String(128)))

    # pushed to agencies or not
    pushed = db.Column(db.Boolean, default=False)

    # deleted bit
    deleted = db.Column(db.Boolean, default=False)

    # relationships
    account = db.relationship('Account', backref=db.backref(
        'newswire_posts', lazy='dynamic'))
    creator = db.relationship('User', backref=db.backref(
        'newswire_posts', lazy='dynamic'),
        foreign_keys='NewswirePost.created_by')
    editor = db.relationship('User', backref=db.backref(
        'updated_newswire_posts', lazy='dynamic'),
        foreign_keys='NewswirePost.updated_by')
    # linked files
    files = db.relationship(
        'NewswirePostLibraryFile', secondary=newswirepostfiles,
        backref=db.backref('newswire_posts', lazy='dynamic'),
        passive_deletes=True)
    logo_file = db.relationship('NewswirePostLibraryFile', backref=db.backref(
        'newswire_logos', lazy='dynamic'),
        foreign_keys='NewswirePost.logo_file_id')

    def __init__(self, *args, **kwargs):
        super(NewswirePost, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<NewswirePost %r>' % (self.heading)
