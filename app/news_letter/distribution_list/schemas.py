"""
Schemas for "market_performance" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for
from marshmallow import (
    fields, validate, pre_dump, post_dump, validates_schema, ValidationError, pre_load)

from app import ma
from app.base import constants as APP
from app.resources.user_profiles import constants as USER_PROFILE
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.news_letter.distribution_list.models import DistributionList
from app.resources.users.models import User
from app.resources.unsubscriptions.models import Unsubscription


class DistributionListSchema(ma.ModelSchema):
    """
    Schema for loading "distribution_list" from request,\
    and also formatting output
    """
    _default_exclude_fields = []
    email = field_for(DistributionList, 'email', field_class=fields.Email)
    first_name = field_for(
        DistributionList, 'first_name', validate=[validate.Length(
            min=1, error=APP.MSG_NON_EMPTY), validate.Length(
            max=USER_PROFILE.NAME_MAX_LENGTH, error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = DistributionList
        include_fk = True
        dump_only = default_exclude

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema',  only=user_fields,
        dump_only=True)
    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=("row_id",
            "account_name"), dump_only=True)
    # unsubscriptions = ma.Nested(
    #     'app.resources.unsubscriptions.schemas.UnsubscriptionSchema',
    #     exclude=['email', 'created_date', 'modified_date','users'], dump_only=True)

    @post_dump
    def unsubscribe_newsletter(self, obj):
        """
        add news object in response
        """
        obj['unsubscribe_newsletter'] = []
        model = Unsubscription.query.filter(Unsubscription.email==obj['email']).first()
        if model:
            if APP.EVNT_NEWS_LETTER in model.events:
                obj['unsubscribe_newsletter'] = True
            else:
                obj['unsubscribe_newsletter'] = False
        else:
            obj['unsubscribe_newsletter'] = False

    # @validates_schema
    # def validate_email(self, data):
    #     """
    #     Validate email(already exist in user table)
    #     """
    #     if 'email' in data:
    #         user = User.query.filter(User.email == data["email"]).first()

    #         if user:
    #             raise ValidationError("Already user exist with mentioned EmailID")


class DistributionListReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "distribution_list" filters from request args
    """
    # standard db fields
    email = fields.String(load_only=True)
    account_id = fields.Integer(load_only=True)
    designation = fields.String(load_only=True)
    account_name = fields.String(load_only=True)
    full_name = fields.String(load_only=True)
    main_filter = fields.String(load_only=True)
    started_at_from = fields.Date(load_only=True)
    ended_at_to = fields.Date(load_only=True)
