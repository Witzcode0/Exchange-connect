"""
Models for "news item archive" package.
"""

from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel


class NewsItemArchive(BaseModel):

    __tablename__ = 'news_item_archive'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='news_item_archive_account_id_fkey',
        ondelete='CASCADE'), nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='news_item_archive_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='news_item_archive_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)
    news_id = db.Column(db.BigInteger, db.ForeignKey(
        'news_item.id', name='news_item_archive_news_id_fkey',
        ondelete='CASCADE'), nullable=False)

    guid = db.Column(db.String(1024), nullable=False)
    title = db.Column(db.String(512), nullable=False)
    link = db.Column(db.String(1024), nullable=False)
    posted_at = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.String(), nullable=False)
    tags = db.Column(db.ARRAY(db.String), nullable=False)
    news_name = db.Column(db.String(512), nullable=False)
    news_url = db.Column(db.String(1024), nullable=False)

    # relationships
    account = db.relationship('Account', backref=db.backref(
        'news_archive', lazy='dynamic'))
    creator = db.relationship(
        'User', backref=db.backref('news_archive', lazy='dynamic'),
        foreign_keys='NewsItemArchive.created_by')
    news = db.relationship('NewsItem', backref=db.backref(
        'news_archive', lazy='dynamic'))
    # special relationship for already archived eager loading check
    news_j = db.relationship('NewsItem', backref=db.backref(
        'news_archived', uselist=False))

    # multi column
    __table_args__ = (
        UniqueConstraint('news_id', 'created_by',
                         name='c_news_id_created_by_key'),
    )

    def __init__(self, guid=None, title=None, link=None,
                 posted_at=None, description=None, *args, **kwargs):
        self.guid = guid
        self.title = title
        self.link = link
        self.posted_at = posted_at
        self.description = description
        super(NewsItemArchive, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<NewsItem archive row_id=%r, guid=%r, title=%r, link=%r>' % (
            self.row_id, self.guid, self.title, self.link)
