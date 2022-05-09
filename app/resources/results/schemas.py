"""
schemas for result master
"""

from app import ma
from app.resources.results.models import AccountResultTracker


class AccountResultTrackerSchema(ma.ModelSchema):
    """
    Schema for loading data from results api
    """
    class Meta:
        model = AccountResultTracker
        include_fk = True
