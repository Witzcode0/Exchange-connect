"""
Models for "project parameters" package.
"""

from sqlalchemy import func, Index

from app import db
from app.base.models import BaseModel
# related model imports done in toolkit/__init__


class ProjectParameter(BaseModel):

    __tablename__ = 'project_parameter'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='project_parameter_created_by_fkey'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='project_parameter_updated_by_fkey'), nullable=False)

    # account id of the project
    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='project_parameter_account_id_fkey'),
        nullable=False)
    project_id = db.Column(db.BigInteger, db.ForeignKey(
        'project.id', name='project_parameter_project_id_fkey',
        ondelete='CASCADE'), nullable=False)
    parent_parameter_name = db.Column(db.String(256), nullable=False)
    parameter_name = db.Column(db.String(256), nullable=False)
    parameter_value = db.Column(db.String(256))
    started_at = db.Column(db.DateTime)
    ended_at = db.Column(db.DateTime)
    level = db.Column(db.Integer, default=1)

    # multi column
    __table_args__ = (
        # unique lower case index, i.e case-insensitive unique constraint
        Index('ci_project_id_parent_parameter_name_parameter_name_key',
              project_id, func.lower(parent_parameter_name),
              func.lower(parameter_name), unique=True),
    )

    # relationships
    project = db.relationship('Project', backref=db.backref(
        'project_parameters', lazy='dynamic', passive_deletes=True))
    creator = db.relationship('User', backref=db.backref(
        'project_parameters', lazy='dynamic'),
        foreign_keys='ProjectParameter.created_by')
    account = db.relationship('Account', backref=db.backref(
        'project_parameters', lazy='dynamic'))

    def __init__(self, project_id=None, parent_parameter_name=None,
                 account_id=None, created_by=None,
                 updated_by=None, parameter_name=None,
                 *args, **kwargs):
        self.project_id = project_id
        self.parent_parameter_name = parent_parameter_name
        self.parameter_name = parameter_name
        self.account_id = account_id
        self.created_by = created_by
        self.updated_by = updated_by
        super(ProjectParameter, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<ProjectParameter %r>' % (self.row_id)
