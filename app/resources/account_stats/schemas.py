"""
Schemas for "account stats" related models
"""


from app import ma
from app.base.schemas import (
    default_exclude, account_fields, BaseReadArgsSchema)
from app.resources.account_stats.models import AccountStats


class AccountStatsSchema(ma.ModelSchema):
    """
    Schema for loading "account stats" from request, and also formatting output
    """

    class Meta:
        model = AccountStats
        include_fk = True
        dump_only = default_exclude

    links = ma.Hyperlinks({
        'collection': ma.URLFor('api.accountstatslist')
    }, dump_only=True)

    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True)


class AccountStatsReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "account stats" filters from request args
    """
    pass
