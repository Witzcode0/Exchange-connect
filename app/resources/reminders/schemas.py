"""
Schemas for "reminder schemas" related models
"""
from app import ma
from app.resources.reminders.models import Reminder
from app.base.schemas import default_exclude


class ReminderSchema(ma.ModelSchema):
    """
    Schema for loading "reminder" from request,\
    and also formatting output
    """
    _default_exclude_fields = []
    
    class Meta:
        model = Reminder
        include_fk = True
        dump_only = default_exclude
