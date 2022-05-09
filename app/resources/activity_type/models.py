"""
Models for "accounts" package.
"""

from sqlalchemy import func, Index
from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel


class ActivityType(BaseModel):
    """
    ActivityType defines name of activity
    """

    __tablename__ = 'activity_type' 
    __global_searchable__ = ['activity_type']

    created_by = db.Column(db.BigInteger, nullable=False)
    updated_by = db.Column(db.BigInteger, nullable=False)
    activity_name = db.Column(db.String(512), nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    deleted = db.Column(db.Boolean,default=False)

    def __init__(self, activity_name=None, is_active=False, *args, **kwargs):
        self.activity_name = activity_name
        self.is_active = is_active
        super(ActivityType, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<ActivityType %r>' % (self.activity_name)
