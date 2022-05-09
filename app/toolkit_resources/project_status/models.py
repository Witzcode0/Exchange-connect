"""
Models for "project_status" package.
"""
from app import db
from app.base.models import BaseModel
from app.resources.users.models import User


class ProjectStatus(BaseModel):
    __tablename__ = 'project_status'
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='project_status_created_by_fkey'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='project_status_updated_by_fkey'), nullable=False)
    name = db.Column(db.String(64), nullable=False)
    code = db.Column(db.String(32), nullable=False, unique=True)
    sequence = db.Column(db.Integer, nullable=False)


    def __init__(self, name=None, code=None, sequence=None, created_by=None,
                 updated_by=None, analyst_id=None, *args, **kwargs):
        self.name = name
        self.code = code
        self.sequence = sequence
        self.created_by = created_by
        self.updated_by = updated_by
        super(ProjectStatus, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<ProjectStatus %r>' % (self.row_id)
