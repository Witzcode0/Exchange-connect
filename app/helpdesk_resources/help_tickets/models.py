"""
Models for "helptickets" package.
"""

import os

from flask import current_app

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString, ChoiceString
from app.common.utils import get_s3_download_link, do_nothing
from app.helpdesk_resources.help_tickets import constants as HTICKET
# related model imports done in helpdesks/__init__


class HelpTicket(BaseModel):

    __tablename__ = 'help_ticket'
    # config key for root folder of attachments
    root_folder_key = 'HTICKET_ATTACH_FOLDER'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='help_ticket_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='help_ticket_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)
    name = db.Column(db.String(128), nullable=False)
    email = db.Column(LCString(128), nullable=False)
    phone = db.Column(db.String(16), nullable=False)
    section = db.Column(ChoiceString(HTICKET.SECTION_TYPES_CHOICES),
                        nullable=False, default=HTICKET.SEC_AC)
    function = db.Column(ChoiceString(HTICKET.FUNCTION_TYPES_CHOICES),
                         nullable=False, default=HTICKET.FXN_HM)
    subject = db.Column(db.String(256), nullable=False)
    description = db.Column(db.String(1024), nullable=False)
    attachment = db.Column(db.String())
    status = db.Column(ChoiceString(HTICKET.STATUS_TYPES_CHOICES),
                       nullable=False, default=HTICKET.TS_PG)
    assignee_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='help_ticket_assignee_id_fkey', ondelete='SET NULL'))
    domain_id = db.Column(db.BigInteger, db.ForeignKey(
        'domain.id', name='help_ticket_domain_id_fkey', ondelete='RESTRICT'),
                          nullable=False)

    # deleted bit
    deleted = db.Column(db.Boolean, default=False)

    # relationships
    creator = db.relationship('User', backref=db.backref(
        'created_tickets', lazy='dynamic'),
        foreign_keys='HelpTicket.created_by')
    assignee = db.relationship('User', backref=db.backref(
        'assigned_tickets', lazy='dynamic'),
        foreign_keys='HelpTicket.assignee_id')

    # dynamic properties
    attachment_url = None

    def __init__(self, created_by=None, name=None, email=None,
                 phone=None, section=None, function=None, subject=None,
                 description=None, *args, **kwargs):
        self.created_by = created_by
        self.name = name
        self.email = email
        self.phone = phone
        self.section = section
        self.function = function
        self.subject = subject
        self.description = description
        super(HelpTicket, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<HelpTicket row_id=%r, created_by=%r, assignee_id=%r>' % (
            self.row_id, self.created_by, self.assignee_id)

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
