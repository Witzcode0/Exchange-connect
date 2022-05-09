"""
Models for "project types" package.
"""

from sqlalchemy import func, Index

from app import db
from app.base.models import BaseModel
# related model imports done in toolkit/__init__


class RefProjectType(BaseModel):

    __tablename__ = 'ref_project_type'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='ref_project_type_created_by_fkey'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='ref_project_type_updated_by_fkey'), nullable=False)

    project_type_name = db.Column(db.String(256), unique=True, nullable=False)
    estimated_delivery_days = db.Column(db.Integer, nullable=False)
    deleted = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # multi column
    __table_args__ = (
        # unique lower case index, i.e case-insensitive unique constraint
        Index('ci_ref_project_type_unique_project_type_name', func.lower(
            project_type_name), unique=True),
    )

    def __init__(self, created_by=None, updated_by=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        super(RefProjectType, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<RefProjectType %r>' % (self.row_id)
