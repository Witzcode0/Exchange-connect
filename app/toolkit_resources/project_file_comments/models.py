"""
Models for "project file comments" package.
"""
from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel


commentusers = db.Table(
    'commentusers',
    db.Column('project_file_comment_id', db.BigInteger, db.ForeignKey(
        'project_file_comment.id', name='project_file_comment_id_fkey',
        ondelete="CASCADE"), nullable=False),
    db.Column('user_id', db.Integer, db.ForeignKey(
        'user.id', name='commentusers_user_id_fkey',
        ondelete="CASCADE"), nullable=False),
    UniqueConstraint('project_file_comment_id', 'user_id',
                     name='ac_project_file_comment_id_user_id_key'),
)


class ProjectFileComment(BaseModel):

    __tablename__ = 'project_file_comment'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='project_archive_file_created_by_fkey'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='project_archive_file_updated_by_fkey'),
        nullable=False)

    comment = db.Column(db.String(1024), nullable=False)
    project_file_id = db.Column(db.BigInteger, db.ForeignKey(
        'project_archive_file.id',
        name='project_file_comment_project_archive_file_id_fkey',
        ondelete='CASCADE'), nullable=False)

    # relationships
    project_archive_file = db.relationship(
        'ProjectArchiveFile', backref=db.backref('comments', lazy='dynamic'),
        foreign_keys='ProjectFileComment.project_file_id')
    creator = db.relationship('User', backref=db.backref(
        'project_file_comments', lazy='dynamic'),
        foreign_keys='ProjectFileComment.created_by')
    seen_comment_users = db.relationship(
        'User', backref=db.backref('seen_file_comments', lazy='dynamic'),
        secondary='commentusers'
    )

    # dynamic boolean to know if the user read the comment
    is_read = True


    def __init__(self, created_by=None, updated_by=None, comment=None,
                 project_file_id=None, *args,
                 **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        self.comment = comment
        self.project_file_id = project_file_id
        super(ProjectFileComment, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<ProjectFileComment %r>' % (self.row_id)
