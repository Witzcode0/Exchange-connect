"""
Schema for global activity
"""
from marshmallow import fields

from app import ma
from app.base.schemas import BaseReadArgsSchema


class GlobalActitvitySchema(ma.Schema):
    """
    Schema for global activity
    """
    row_id = fields.Integer(dump_only=True)
    creator_name = fields.String(dump_only=True)
    modifier_name = fields.String(dump_only=True)
    name = fields.String(dump_only=True)
    activity_type = fields.String(dump_only=True)
    created_date = fields.DateTime(dump_only=True)
    modified_date = fields.DateTime(dump_only=True)
    link = ma.Url(dump_only=True, default='#')


class GlobalActivityReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "global activity" filters from request args
    """
    # Todo :- default sort to modified_date
    name = fields.String(load_only=True)
