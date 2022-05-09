"""
Models for "crm contacts" package.
"""

import os

from flask import current_app
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import load_only

from app import db
from app.base.models import BaseModel
from app.common.utils import get_s3_download_link, do_nothing
from app.base.model_fields import ChoiceString, LCString
from app.resources.accounts import constants as ACCOUNT
from app.resources.industries.models import Industry


class FundManagement(BaseModel):
    """
    create FundManagement
    """

    __tablename__ = 'fundmanagement'

    crm_contact_id = db.Column(db.BigInteger, db.ForeignKey(
        'crm_contact.id', name='fundmanagement_crm_contact_id_fkey', ondelete="CASCADE"),
    nullable=False)
    entity_proper_name = db.Column(db.String(), nullable=False)
    factset_fund_id = db.Column(db.String(), nullable=True)

    # __table_args__ = (
    #     UniqueConstraint('crm_contact_id', 'fund', 'is_profile',
    #                  name='ac_fund_management_key'),
    # )

    def __init__(self,crm_contact_id=None,entity_proper_name=None, *args, **kwargs):
        self.crm_contact_id = crm_contact_id
        self.entity_proper_name = entity_proper_name
        super(FundManagement, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<FundManagement %s>' % (self.fund)

class CRMContact(BaseModel):

    __tablename__ = 'crm_contact'
    __global_searchable__ = ['first_name', 'last_name', 'middle_name',
                             'company', 'designation', 'created_by']
    root_profile_photo_folder_key = 'CRM_CONTACT_PROFILE_PHOTO_FOLDER'

    account_id = db.Column(db.Integer, db.ForeignKey('account.id'),
                           nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'),
                           nullable=False)
    user_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='crm_contact_user_id_fkey', ondelete='CASCADE'),
                        nullable=False)
    email = db.Column(LCString(128), nullable=False)
    first_name = db.Column(db.String(128), nullable=False)
    middle_name = db.Column(db.String(128))
    last_name = db.Column(db.String(128))
    contact_type = db.Column(ChoiceString(ACCOUNT.CRM_ACCT_TYPES_CHOICES),
                             nullable=False)

    company = db.Column(db.String(128))
    designation = db.Column(db.String(128))
    phone_number = db.Column(db.String(50))
    alternet_phone_number = db.Column(db.String(50))
    # address details
    address_street_one = db.Column(db.String(256))
    address_street_two = db.Column(db.String(256))
    address_city = db.Column(db.String(128))
    address_state = db.Column(db.String(128))
    address_zip_code = db.Column(db.String(128))
    address_country = db.Column(db.String(128))
    #
    # fund_managed = db.Column(db.ARRAY(db.String()))
    equity_focus = db.Column(db.String())
    industry_coverage = db.Column(db.ARRAY(db.Integer()))

    profile_photo = db.Column(db.String())
    profile_thumbnail = db.Column(db.String())

    # Factset data
    is_company_profile = db.Column(db.Boolean, default=False)
    factset_person_id = db.Column(db.String(128))

    about = db.Column(db.String())

    # for system user
    is_system_user = db.Column(db.Boolean, default=False)


    # multi column
    __table_args__ = (
        UniqueConstraint('created_by', 'email',
                         name='crm_cont_created_by_email_key'),)
    # relationship
    creator = db.relationship('User', backref=db.backref(
        'crm_contacts', lazy='dynamic'), foreign_keys='CRMContact.created_by')
    user = db.relationship('User', backref=db.backref(
        'crm_users', lazy='dynamic'), foreign_keys='CRMContact.user_id')
    # linked fund management
    fund_management = db.relationship('FundManagement', backref=db.backref(
            'crm_contact_fund_management'),
    primaryjoin='FundManagement.crm_contact_id == CRMContact.row_id', passive_deletes=True)

    # dynamic properties
    profile_photo_url = None
    profile_thumbnail_url = None
    industry_coverages = None

    def __init__(self, email=None, first_name=None, last_name=None,
                 created_by=None, *args, **kwargs):
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.created_by = created_by
        super(CRMContact, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CRMContact %r>' % (self.row_id)

    def load_urls(self, with_redirect=False, expires_in=3600,
                  thumbnail_only=False):
        """
        Populates the profile_photo_url, profile_thumbnail_url
        dynamic properties
        """
        s3_url = ''
        thumbnail_bucket_name = ''
        if not self.profile_photo and not self.profile_thumbnail:
            return
        sub_folder = self.file_subfolder_name()
        if current_app.config['S3_UPLOAD']:
            if self.profile_thumbnail:
                thumbnail_bucket_name = current_app.config[
                    'S3_THUMBNAIL_BUCKET']
                s3_url = 'https://s3-ap-southeast-1.amazonaws.com/'
            signer = get_s3_download_link
        else:
            signer = do_nothing
        if self.profile_thumbnail:
            self.profile_thumbnail_url = os.path.join(
                s3_url, thumbnail_bucket_name,
                current_app.config[self.root_profile_photo_folder_key],
                sub_folder, self.profile_thumbnail)
        if thumbnail_only:
            return
        if self.profile_photo:
            self.profile_photo_url = signer(os.path.join(
                current_app.config[self.root_profile_photo_folder_key],
                sub_folder, self.profile_photo), expires_in=expires_in)
        return

    def load_industry_coverage(self):
        """
        Populates the linked_contacts dynamic property
        """
        self.industry_coverages = []
        if self.industry_coverage:
            self.industry_coverages = [
                i for i in Industry.query.filter(
                    Industry.row_id.in_(
                        [iid for iid in self.industry_coverage])).options(
                        load_only('row_id', 'name')).all()]
        return self.industry_coverages
