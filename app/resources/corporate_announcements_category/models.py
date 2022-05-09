"""
Models for "corporate announcements" package.
"""
from sqlalchemy import func, Index

from app import db
from app.base.models import BaseModel


class CorporateAnnouncementCategory(BaseModel):
    """
    corporate announcement category keyword
    """
    __tablename__ = 'corporate_announcement_category'


    name = db.Column(db.String(), unique=True, nullable=True)

    # keywords column for particular category
    subject_keywords = db.Column(db.ARRAY(db.String()), default=[])
    category_keywords = db.Column(db.ARRAY(db.String()), default=[])

    created_by = db.Column(db.Integer, db.ForeignKey('user.id'),
                           nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'),
                           nullable=False)
    bse_keywords = db.Column(db.ARRAY(db.String()), default=[])

    bse_keywords = db.Column(db.ARRAY(db.String()), default=[])

    # deleted bit
    deleted = db.Column(db.Boolean, default=False)

    # relationships
    creator = db.relationship('User', backref=db.backref(
        'announcements_category', lazy='dynamic'),
        foreign_keys='CorporateAnnouncementCategory.created_by')
    editor = db.relationship('User', backref=db.backref(
        'updated_announcements_category', lazy='dynamic'),
        foreign_keys='CorporateAnnouncementCategory.updated_by')

    __table_args__ = (
        # unique lower case index, i.e case-insensitive unique constraint
        Index('ci_corporate_announcement_category_unique_name', func.lower(name),
              unique=True),
    )

    def __init__(self, category=None, *args, **kwargs):

        self.name = category
        super(CorporateAnnouncementCategory, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CorporateAnnouncementCategory %r>' % (self.name)