"""
Models for "helpcomments" package.
"""

import os

from flask import current_app

from app import db
from app.common.utils import get_s3_download_link, do_nothing
from app.base.models import BaseModel
# related model imports done in helpdesks/__init__


class HelpComment(BaseModel):

    __tablename__ = 'help_comment'
    # config key for root folder of attachments
    root_folder_key = 'HCOMMENT_ATTACH_FOLDER'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='help_comment_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='help_comment_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    ticket_id = db.Column(db.BigInteger, db.ForeignKey(
        'help_ticket.id', name='help_comment_ticket_id_fkey',
        ondelete='CASCADE'), nullable=False)
    message = db.Column(db.String(1024), nullable=False)
    attachment = db.Column(db.String())

    # deleted bit
    deleted = db.Column(db.Boolean, default=False)

    # relationships
    creator = db.relationship('User', backref=db.backref(
        'created_comments', lazy='dynamic'),
        foreign_keys='HelpComment.created_by')
    ticket = db.relationship('HelpTicket', backref=db.backref(
        'comments', lazy='dynamic'))

    # dynamic properties
    attachment_url = None

    def __init__(self, created_by=None, ticket_id=None, message=None,
                 *args, **kwargs):
        self.created_by = created_by
        self.ticket_id = ticket_id
        self.message = message
        super(HelpComment, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<HelpComment row_id=%r, created_by=%r, ticket_id=%r>' % (
            self.row_id, self.created_by, self.ticket_id)

    def load_urls(self, with_redirect=False, expires_in=3600):
        """
        Populates the attachment_url dynamic property
        """
        if not self.attachment:
            return
        sub_folder = self.file_subfolder_name()
        if current_app.config['S3_UPLOAD']:
            signer = get_s3_download_link
        else:
            signer = do_nothing
        if self.attachment:
            self.attachment_url = signer(os.path.join(
                current_app.config[self.root_folder_key], sub_folder,
                self.attachment), expires_in=expires_in)
        return
