"""
Models for "descriptor" package.
"""
from sqlalchemy import UniqueConstraint
from app.resources.corporate_announcements_category.models import CorporateAnnouncementCategory

from app import db
from app.base.models import BaseModel

class BSE_Descriptor(BaseModel):
    __tablename__ = 'descriptor_master'

    descriptor_id = db.Column(db.Integer)
    descriptor_name = db.Column(db.String)
    cat_id = db.Column(db.Integer, db.ForeignKey('corporate_announcement_category.id'))
    deleted = db.Column(db.Boolean, default=False)

    category = db.relationship('CorporateAnnouncementCategory',
               uselist=False,
               backref=db.backref('cat_id', lazy='dynamic'))
