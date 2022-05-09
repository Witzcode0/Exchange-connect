"""
Models for "project designers" package.
"""

from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel
# related model imports done in toolkit/__init__


class ProjectDesigner(BaseModel):

    __tablename__ = 'project_designer'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='project_designer_created_by_fkey'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='project_designer_updated_by_fkey'), nullable=False)

    project_id = db.Column(db.BigInteger, db.ForeignKey(
        'project.id', name='project_designer_project_id_fkey',
        ondelete='CASCADE'), nullable=False)
    designer_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='project_designer_designer_id_fkey'), nullable=False)

    # multi column
    __table_args__ = (
        UniqueConstraint('project_id', 'designer_id',
                         name='c_project_id_designer_id_key'),
    )

    # relationships
    designed_project = db.relationship('Project', backref=db.backref(
        'project_designers', lazy='dynamic', passive_deletes=True))
    designer = db.relationship('User', backref=db.backref(
        'designed_projects', lazy='dynamic'),
        foreign_keys='ProjectDesigner.designer_id')
    creator = db.relationship('User', backref=db.backref(
        'project_designers_created', lazy='dynamic'),
        foreign_keys='ProjectDesigner.created_by')

    def __init__(self, project_id=None, created_by=None, updated_by=None,
                 designer_id=None, *args, **kwargs):
        self.project_id = project_id
        self.designer_id = designer_id
        self.created_by = created_by
        self.updated_by = updated_by
        super(ProjectDesigner, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<ProjectDesigner %r>' % (self.row_id)
