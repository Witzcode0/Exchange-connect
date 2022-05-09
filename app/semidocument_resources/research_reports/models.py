"""
Models for "research report" package.
"""
import os

from flask import current_app
from sqlalchemy import UniqueConstraint

from app import db
from app.common.utils import get_s3_download_link, do_nothing
from app.base.models import BaseModel
from app.resources.corporate_announcements.models import CorporateAnnouncement

# association table for many-to-many Research Report Announcements
researchreportannouncements = db.Table(
    'researchreportannouncements',
    db.Column('research_report_id', db.BigInteger, db.ForeignKey(
        'research_report.id',
        name='resreportannouns_research_report_id_fkey', ondelete="CASCADE"),
        nullable=False),
    db.Column('announcement_id', db.BigInteger, db.ForeignKey(
        'corporate_announcement.id', name='resreportannouns_announces_id_fkey',
        ondelete="CASCADE"), nullable=False),
    UniqueConstraint('research_report_id', 'announcement_id',
                     name='ra_research_report_id_announcement_id_key'),
)


class ResearchReport(BaseModel):

    __tablename__ = 'research_report'
    __global_searchable__ = ['subject', 'created_by', 'file', 'url',
                             'research_report_date']
    # config key for root folder of files
    root_folder_key = 'RESEARCH_REPORT_FILE_FOLDER'

    account_id = db.Column(db.Integer, db.ForeignKey('account.id'),
                           nullable=False)

    corporate_account_id = db.Column(db.Integer, db.ForeignKey('account.id'),
                                     nullable=False)

    created_by = db.Column(db.Integer, db.ForeignKey('user.id'),
                           nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'),
                           nullable=False)
    research_report_date = db.Column(db.Date, nullable=False)

    subject = db.Column(db.String(512))
    description = db.Column(db.String(2048))

    # check if both of these are present
    file = db.Column(db.String())
    xml_file = db.Column(db.String())
    url = db.Column(db.String(256))
    thumbnail_name = db.Column(db.String())

    # deleted bit
    deleted = db.Column(db.Boolean, default=False)

    # temporary
    stock_chart = db.Column(db.Boolean, default=True)
    key_stat = db.Column(db.Boolean, default=True)
    chart_start_date = db.Column(db.String(32))
    chart_end_date = db.Column(db.String(32))

    # relationships
    announcements = db.relationship(
        'CorporateAnnouncement', secondary=researchreportannouncements,
        backref=db.backref('research_reports', lazy='dynamic'),
        passive_deletes=True)
    account = db.relationship('Account', backref=db.backref(
        'research_reports_created', lazy='dynamic'),
        foreign_keys='ResearchReport.account_id')
    corporate_account = db.relationship('Account', backref=db.backref(
        'research_reports', lazy='dynamic'),
        foreign_keys='ResearchReport.corporate_account_id')
    creator = db.relationship('User', backref=db.backref(
        'research_reports', lazy='dynamic'),
        foreign_keys='ResearchReport.created_by')
    editor = db.relationship('User', backref=db.backref(
        'updated_research_reports', lazy='dynamic'),
        foreign_keys='ResearchReport.updated_by')

    # dynamic properties
    file_url = None
    thumbnail_url = None
    xml_file_url = None

    def __init__(self,  *args, **kwargs):
        super(ResearchReport, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<ResearchReport %r>' % (self.subject)

    def load_urls(self, with_redirect=False, expires_in=3600,
                  thumbnail_only=False):
        """
        Populates the file_url dynamic properties
        """
        s3_url = ''
        thumbnail_bucket_name = ''
        if not any([self.file, self.thumbnail_name, self.xml_file]):
            return
        sub_folder = self.file_subfolder_name()
        if current_app.config['S3_UPLOAD']:
            if self.thumbnail_name:
                thumbnail_bucket_name = current_app.config[
                    'S3_THUMBNAIL_BUCKET']
                s3_url = 'https://s3-ap-southeast-1.amazonaws.com/'
            signer = get_s3_download_link
        else:
            signer = do_nothing
        if self.thumbnail_name:
            self.thumbnail_url = os.path.join(
                s3_url, thumbnail_bucket_name,
                current_app.config[self.root_folder_key],
                sub_folder, self.thumbnail_name)
        if thumbnail_only:
            return
        if self.file:
            self.file_url = signer(os.path.join(
                current_app.config[self.root_folder_key],
                sub_folder, self.file), expires_in=expires_in)
        if self.xml_file:
            self.xml_file_url = signer(os.path.join(
                current_app.config[self.root_folder_key],
                sub_folder, self.xml_file), expires_in=expires_in)
        return
