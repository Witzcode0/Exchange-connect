"""
Schemas for "cronjob" related models
"""

import re
from marshmallow import ValidationError, validates_schema
from marshmallow import fields, validate, pre_dump
from datetime import datetime

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.resources.cron_job.models import CronJob
from app.resources.cron_job import constants as CRON


class CronJobSchema(ma.ModelSchema):
    """
    Schema for loading "crontab" from requests, and also formatting output
    """

    # default fields to exclude from the schema for speed up
    _default_exclude_fields = ['command','cr_user','timezone']

    class Meta:
        model = CronJob
        load_only = ('updated_by', 'created_by','cr_user')
        dump_only = default_exclude + ('updated_by', 'created_by','cr_user')

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    domain = ma.Nested(
        'app.domain_resources.domains.schemas.DomainSchema', only=('row_id','country'),
        dump_only=True)

    hours = ma.String(dump_only=True)
    minutes = ma.String(dump_only=True)

    @pre_dump(pass_many=True)
    def load_time(self, objs, many):
        """
        Loads the time of script
        """
        if many:
            for obj in objs:
                obj.load_time()
        else:
            objs.load_time()

    @validates_schema(pass_original=True)
    def validate_inputs(self, data, original_data):
        """
        Validate inputs exits or not and valid input are exists or not
        """
        error = False
        missing = []
        missing_fields = ['minutes','hours']

        if 'cron_time' in original_data and original_data['cron_time']:
            if not 0<= original_data['cron_time'].minute <= 59:
                missing.append('minute in time')
            if not 0<= original_data['cron_time'].hour <=23:
                missing.append('hour in time')
        else:
            raise ValidationError("You must provide either minutes or hours")

        if 'day_of_month' in original_data and original_data['day_of_month']:
            if original_data['day_of_month']:
                data = []
                if ',' in original_data['day_of_month']:
                    data = original_data['day_of_month'].split(",")
                else:
                    data = [original_data['day_of_month']]
                for sub_data in data:
                    if '-' in sub_data:
                        days_list = sub_data.split("-")
                        if not (1<= int(days_list[0]) <=31 and 1<= int(days_list[1]) <=31):
                            missing.append('day_of_month')
                    elif '/' in sub_data:
                        days_list = sub_data.split('/')
                        if not 1<= int(days_list[1]) <=31:
                            missing.append('day_of_month')
                    else:
                        if not 1<= int(sub_data)<= 31:
                            missing.append('day_of_month')

        if 'month' in original_data and original_data['month']:
            if original_data['month']:
                data = []
                if ',' in original_data['month']:
                    data = original_data['month'].split(",")
                else:
                    data = [original_data['month']]
                for sub_data in data:
                    if '-' in sub_data:
                        days_list = sub_data.split("-")
                        if not (1<= int(days_list[0]) <=12 and 1<= int(days_list[1]) <=12):
                            missing.append('month')
                    elif '/' in sub_data:
                        days_list = sub_data.split('/')
                        if not 1<= int(days_list[1]) <=12:
                            missing.append('month')
                    else:
                        if not 1<= int(sub_data) <= 12:
                            missing.append('month')

        if 'day_of_week' in original_data and original_data['day_of_week']:
            if original_data['day_of_week']:
                data = []
                if ',' in original_data['day_of_week']:
                    data = original_data['day_of_week'].split(",")
                else:
                    data = [original_data['day_of_week']]
                for sub_data in data:
                    if '-' in sub_data:
                        days_list = sub_data.split("-")
                        if not (0<= int(days_list[0]) <=6 and 0<= int(days_list[1]) <=6):
                            missing.append('day_of_week')
                    elif '/' in sub_data:
                        days_list = sub_data.split('/')
                        if not 0<= int(days_list[1]) <=6:
                            missing.append('day_of_week')
                    else:
                        if not 0<= int(sub_data)<=6:
                            missing.append('day_of_week')

        if missing:
            raise ValidationError(
                '%s: are not a proper input' % missing)


class CronJobReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "Cronjob" filters from request args
    """
    is_deactive = fields.Boolean(load_only=True)
