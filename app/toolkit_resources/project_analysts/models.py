"""
Models for "project analysts" package.
"""

from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel
# related model imports done in toolkit/__init__


class ProjectAnalyst(BaseModel):

    __tablename__ = 'project_analyst'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='project_analyst_created_by_fkey'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='project_analyst_updated_by_fkey'), nullable=False)

    project_id = db.Column(db.BigInteger, db.ForeignKey(
        'project.id', name='project_analyst_project_id_fkey',
        ondelete='CASCADE'), nullable=False)
    analyst_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='project_analyst_analyst_id_fkey'), nullable=False)

    # multi column
    __table_args__ = (
        UniqueConstraint('project_id', 'analyst_id',
                         name='c_project_id_analyst_id_key'),
    )

    # relationships
    assigned_project = db.relationship('Project', backref=db.backref(
        'project_analysts', lazy='dynamic', passive_deletes=True))
    analyst = db.relationship('User', backref=db.backref(
        'assigned_projects', lazy='dynamic'),
        foreign_keys='ProjectAnalyst.analyst_id')
    creator = db.relationship('User', backref=db.backref(
        'project_analysts', lazy='dynamic'),
        foreign_keys='ProjectAnalyst.created_by')

    def __init__(self, project_id=None, created_by=None, updated_by=None,
                 analyst_id=None, *args, **kwargs):
        self.project_id = project_id
        self.analyst_id = analyst_id
        self.created_by = created_by
        self.updated_by = updated_by
        super(ProjectAnalyst, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<ProjectAnalyst %r>' % (self.row_id)
