"""
Models for "project screen sharing" package.
"""

from app import db
from app.base.models import BaseModel
# related model imports done in toolkit/__init__


class ProjectScreenSharing(BaseModel):

    __tablename__ = 'project_screen_sharing'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='project_screen_sharing_created_by_fkey'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='project_screen_sharing_updated_by_fkey'),
        nullable=False)

    # account id of the project
    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='project_screen_sharing_account_id_fkey'),
        nullable=False)
    project_id = db.Column(db.BigInteger, db.ForeignKey(
        'project.id', name='project_screen_sharing_project_id_fkey',
        ondelete='CASCADE'), nullable=False)
    sent_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='project_screen_sharing_sent_by_fkey'),
        nullable=False)
    scheduled_at = db.Column(db.DateTime, nullable=False)
    estimated_ended_at = db.Column(db.DateTime)
    project_parameter_id = db.Column(db.BigInteger, db.ForeignKey(
        'project_parameter.id',
        name='project_screen_sharing_project_parameter_id_fkey'))
    remarks = db.Column(db.String(1024))

    actual_ended_at = db.Column(db.DateTime)

    # relationships
    creator = db.relationship('User', backref=db.backref(
        'project_screen_sharing', lazy='dynamic'),
        foreign_keys='ProjectScreenSharing.created_by')
    project_parameter = db.relationship('ProjectParameter', backref=db.backref(
        'project_screen_sharing', lazy='dynamic'),
        foreign_keys='ProjectScreenSharing.project_parameter_id')

    def __init__(self, created_by=None, updated_by=None, account_id=None,
                 project_id=None, sent_by=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        self.account_id = account_id
        self.project_id = project_id
        self.sent_by = sent_by
        super(ProjectScreenSharing, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<ProjectScreenSharing %r>' % (self.row_id)
