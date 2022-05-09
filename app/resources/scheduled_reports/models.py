"""
Models for "corporate announcements" package.
"""
import datetime

from sqlalchemy.dialects.postgresql import JSONB
from dateutil.relativedelta import relativedelta

from app import db
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString, LCString, CastingArray
from app.resources.scheduled_reports import constants as SCH_REPORT


class ScheduledReport(BaseModel):

    __tablename__ = 'scheduled_report'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='scheduled_report_account_id_fkey',
        ondelete='CASCADE'), nullable=False)
    company = db.Column(db.String(128), nullable=False)
    peers = db.Column(CastingArray(JSONB))
    email = db.Column(LCString(128), nullable=False)
    type = db.Column(ChoiceString(SCH_REPORT.SCH_REPORT_TYPE_CHOICES),
                     nullable=False)
    frequency = db.Column(ChoiceString(SCH_REPORT.FREQUENCT_TYPE_CHOICES),
                          nullable=False)
    request_body = db.Column(JSONB)
    currency = db.Column(db.String(32))
    start_from = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    next_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    # deleted bit
    deleted = db.Column(db.Boolean, default=False)

    created_by = db.Column(db.Integer, db.ForeignKey('user.id'),
                           nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'),
                           nullable=False)

    creator = db.relationship('User', backref=db.backref(
        'scheduled_reports', lazy='dynamic'),
        foreign_keys='ScheduledReport.created_by')
    updator = db.relationship('User', backref=db.backref(
        'updated_scheduled_reports', lazy='dynamic'),
        foreign_keys='ScheduledReport.updated_by')
    account = db.relationship('Account', backref=db.backref(
        'scheduled_reports', lazy='dynamic'),
        foreign_keys='ScheduledReport.account_id')

    def __init__(self,  *args, **kwargs):
        super(ScheduledReport, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<ScheduledReport {} {}>'.format(self.row_id, self.company)

    def calculate_next_at(self):
        if self.next_at:
            next_time_delta = relativedelta(
                **{SCH_REPORT.TIMEDELTA_PARAMS[self.frequency]: 1})
            self.next_at = self.next_at + next_time_delta
        else:
            self.next_at = self.start_from


class ScheduledReportLog(BaseModel):

    __tablename__ = 'scheduled_report_log'

    report_id = db.Column(db.BigInteger, db.ForeignKey(
        'scheduled_report.id', name='scheduled_report_log_report_id_fkey',
        ondelete='CASCADE'))
    sent_at = db.Column(db.DateTime)
    status = db.Column(ChoiceString(SCH_REPORT.SCH_REPORT_STATUS_CHOICES),
                       nullable=False, default=SCH_REPORT.SENT)
    response_code = db.Column(db.Integer)
    response_body = db.Column(db.String())
    api_calls = db.Column(CastingArray(JSONB))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'),
                           nullable=False)
    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='scheduled_report_log_account_id_fkey',
        ondelete='CASCADE'), nullable=False)

    report = db.relationship('ScheduledReport', backref=db.backref(
        'logs', lazy='dynamic',
        order_by='desc(ScheduledReportLog.created_date)'),
        foreign_keys='ScheduledReportLog.report_id')

    def __init__(self,  *args, **kwargs):
        super(ScheduledReportLog, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<ScheduledReportLog {}>'.format(self.row_id)
