"""
Models for "crm groups" package.
"""

import os

from flask import current_app
from sqlalchemy import UniqueConstraint

from app import db
from app.common.utils import get_s3_download_link, do_nothing
from app.base.models import BaseModel
from app.resources.accounts import constants as ACCT

# association table for many-to-many CRMGroup users
groupcontacts = db.Table(
    'groupcontacts',
    db.Column('crm_group_id', db.BigInteger, db.ForeignKey(
        'crm_group.id', name='groupcontacts_crm_group_id_fkey',
        ondelete="CASCADE"), nullable=False),
    db.Column('contact_id', db.BigInteger, db.ForeignKey(
        'user.id', name='groupcontacts_contact_id_fkey',
        ondelete="CASCADE"), nullable=False),
    UniqueConstraint('crm_group_id', 'contact_id',
                     name='groupcontacts_crm_group_id_contact_id_key'),
)


class CRMGroup(BaseModel):

    __tablename__ = 'crm_group'
    root_icon_folder_key = 'CRM_GROUP_ICON_FOLDER'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='crm_library_file_account_id_fkey',
        ondelete='CASCADE'), nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='crm_library_file_created_by_fkey',
        ondelete='CASCADE'), nullable=False)

    group_name = db.Column(db.String(128), nullable=False)
    group_icon = db.Column(db.String())

    # linked contact
    group_contacts = db.relationship(
        'User', secondary=groupcontacts, backref=db.backref(
            'crmgroups', lazy='dynamic', ),
        foreign_keys='[groupcontacts.c.contact_id,groupcontacts.c.crm_group_id]',
        primaryjoin='groupcontacts.c.crm_group_id==CRMGroup.row_id',
        secondaryjoin='and_(groupcontacts.c.contact_id==User.row_id,'
                      'User.deleted==False)',
        passive_deletes=True)
    group_crm_contacts = db.relationship(
        'CRMContact', secondary=groupcontacts,
        backref=db.backref('crmcontactgrouped', lazy='dynamic'),
        foreign_keys='[groupcontacts.c.crm_group_id, '
                     'groupcontacts.c.contact_id]',
        primaryjoin="and_(groupcontacts.c.crm_group_id == CRMGroup.row_id,"
                    "CRMContact.created_by == CRMGroup.created_by,"
                    "CRMContact.contact_type != '"+ACCT.ACCT_SME+"',"
                    "CRMContact.contact_type != '"+ACCT.ACCT_PRIVATE+"')",
        secondaryjoin="and_(groupcontacts.c.contact_id == CRMContact.user_id,)",
        viewonly=True)
    group_crm_connections = db.relationship(
        'Contact', secondary=groupcontacts,
        backref=db.backref('crmconnectiongrouped', lazy='dynamic'),
        foreign_keys='[groupcontacts.c.crm_group_id, '
                     'groupcontacts.c.contact_id]',
        primaryjoin="and_(groupcontacts.c.crm_group_id == CRMGroup.row_id,"
                    "or_(Contact.sent_to == CRMGroup.created_by,"
                    "Contact.sent_by == CRMGroup.created_by))",
        secondaryjoin="or_(and_("
                      "groupcontacts.c.contact_id == Contact.sent_by,"
                      "Contact.sent_to == CRMGroup.created_by),"
                      "and_(groupcontacts.c.contact_id == Contact.sent_to,"
                      "Contact.sent_by == CRMGroup.created_by))",
        viewonly=True)
    # relationship
    account = db.relationship('Account', backref=db.backref(
        'crmgroups', lazy='dynamic'))
    creator = db.relationship(
        'User', backref=db.backref('crmusergroups', lazy='dynamic'),
        foreign_keys='CRMGroup.created_by')
    group_j = db.relationship(
        'User', secondary='groupcontacts', backref=db.backref(
            'crm_contact_grouped', lazy='dynamic'),
        foreign_keys='[groupcontacts.c.crm_group_id, '
                     'groupcontacts.c.contact_id]',
        primaryjoin="groupcontacts.c.crm_group_id == CRMGroup.row_id",
        secondaryjoin="groupcontacts.c.contact_id == User.row_id",
        viewonly=True)

    # dynamic properties
    group_icon_url = None

    def __init__(self, group_name=None, created_by=None, *args, **kwargs):
        self.group_name = group_name
        self.created_by = created_by
        super(CRMGroup, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CRMGroup %r>' % (self.group_name)

    def load_urls(self, with_redirect=False, expires_in=3600,
                  thumbnail_only=False):
        """
        Populates the profile_photo_url, profile_thumbnail_url
        dynamic properties
        """
        s3_url = ''
        if not self.group_icon:
            return
        sub_folder = self.file_subfolder_name()
        if current_app.config['S3_UPLOAD']:
            signer = get_s3_download_link
        else:
            signer = do_nothing
        if self.group_icon:
            self.group_icon_url = signer(os.path.join(
                current_app.config[self.root_icon_folder_key],
                sub_folder, self.group_icon), expires_in=expires_in)
        return
