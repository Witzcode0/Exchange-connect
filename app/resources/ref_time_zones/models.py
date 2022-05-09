"""
Models for "time zone" package.
"""

from sqlalchemy import func, Index
from sqlalchemy.dialects.postgresql import ARRAY

from app import db
from app.base.models import BaseModel


class RefTimeZone(BaseModel):

    __tablename__ = 'ref_time_zone'

    timezone_value = db.Column(db.String(128))
    offset = db.Column(db.String(32))
    display_value = db.Column(db.String(256), nullable=False)
    utc = db.Column(ARRAY(db.String(256)), nullable=False)

    __table_args__ = (
        # unique lower case index, i.e case-insensitive unique constraint
        Index('ci_ref_time_zone_unique_display_value',
              func.lower(display_value), unique=True),
    )

    def __init__(self, display_value=None, utc=None, *args, **kwargs):
        self.display_value = display_value
        self.utc = utc
        super(RefTimeZone, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<RefTimeZone %r>' % (self.row_id)
