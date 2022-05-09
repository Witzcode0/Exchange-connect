"""
Models for "cronjob" package.
"""
import datetime
from sqlalchemy import Index, func

from app import db
from app.base.models import BaseModel
from app.resources.cron_job import constants as CRON
from app.base.model_fields import ChoiceString
from sqlalchemy.types import TIMESTAMP

from app.domain_resources.domains.models import Domain

class CronJob(BaseModel):

    __tablename__ = 'cron_job'

    # minutes = db.Column(db.String())
    # hours = db.Column(db.String())
    day_of_month = db.Column(db.String())
    month = db.Column(db.String())
    day_of_week = db.Column(db.String())
    command = db.Column(db.String(), nullable=False)
    cron_type = db.Column(ChoiceString(CRON.CRONJOB_TYPES), nullable=False)
    is_deactive = db.Column(db.Boolean, default=True)
    time = db.Column(db.Time, nullable=True)
    each = db.Column(ChoiceString(CRON.CRONJOB_EACH_TYPES), nullable=True)
    name = db.Column(db.String(), nullable=False)
    timezone = db.Column(db.String(), nullable=True)
    cr_user = db.Column(db.String(), nullable=False)
    domain_id = db.Column(db.BigInteger, db.ForeignKey(
        'domain.id', name='cron_job_domain_id_fkey'), nullable=True)

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='cron_job_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='cron_job_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)
    domain = db.relationship('Domain', backref=db.backref(
        'cron_job_domain', lazy='dynamic'),
    foreign_keys='CronJob.domain_id')

    hours = None
    minutes = None

    def load_time(self):
        """
        Populates the hours and minutes dynamic properties
        """
        if (not self.time):
            return
        hours = "00"
        minutes = "00"
        if self.time:
            minutes = '0'+str(self.time.minute) if len(str(self.time.minute))<2 else str(self.time.minute)
            hours = '0'+str(self.time.hour) if len(str(self.time.hour)) < 2 else str(self.time.hour)
        self.hours = hours
        self.minutes = minutes
        return

    def __init__(self, cron_type, *args, **kwargs):
        self.cron_type = cron_type
        super(CronJob, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CronJob %r>' % (self.row_id)
