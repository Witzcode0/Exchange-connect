"""
Models for "project chats" package.
"""

from app import db
from app.base.models import BaseModel
# related model imports done in toolkit/__init__


class ProjectChatMessage(BaseModel):

    __tablename__ = 'project_chat_message'

    project_id = db.Column(db.BigInteger, db.ForeignKey(
        'project.id', name='project_chat_message_project_id_fkey',
        ondelete='CASCADE'), nullable=False)
    sent_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='project_chat_message_sent_by_fkey'),
        nullable=False)
    message = db.Column(db.String(1024))

    # relationships
    project = db.relationship('Project', backref=db.backref(
        'project_chats', lazy='dynamic', passive_deletes=True))
    sender = db.relationship('User', backref=db.backref(
        'project_chats', lazy='dynamic'))

    def __init__(self, project_id=None, sent_by=None, *args, **kwargs):
        self.project_id = project_id
        self.sent_by = sent_by
        super(ProjectChatMessage, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<ProjectChatMessage %r>' % (self.row_id)
