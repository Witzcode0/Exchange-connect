"""
Models for "e-meeting comment" package.
"""

from app import db
import datetime
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString
from app.toolkit_resources.project_e_meeting_comment import constants as CATEGORY
from app.toolkit_resources.project_e_meeting.models import Emeeting
# related model imports done in toolkit/__init__


class EmeetingComment(BaseModel):

    __tablename__ = 'e_meeting_comment'

    e_meeting_id = db.Column(db.BigInteger, db.ForeignKey(
        'e_meeting.id', name='e_meeting_comment_id_fkey',
        ondelete='CASCADE'), nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='e_meeting_comment_created_by_fkey'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id',
        name='e_meeting_comment_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)
    status = db.Column(ChoiceString(
        CATEGORY.E_MEETING_STATUS_CHOICES))
    comment = db.Column(db.String(1024))
    meeting_datetime = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    deleted = db.Column(db.Boolean, default=False)

    # relationships
    e_meeting = db.relationship('Emeeting', backref=db.backref(
        'project_meeting_comment', lazy='dynamic', passive_deletes=True))
    creator = db.relationship('User', backref=db.backref(
        'user_comment', lazy='dynamic'),
        foreign_keys='EmeetingComment.created_by')

    def __init__(self, e_meeting_id=e_meeting_id, created_by=None, *args,
                 **kwargs):
        self.e_meeting_id = e_meeting_id
        self.created_by = created_by
        super(EmeetingComment, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<EmeetingComment %r>' % (self.row_id)
