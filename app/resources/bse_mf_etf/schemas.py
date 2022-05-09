"""
Schemas for "bse corporate data" related models
"""
from marshmallow import fields
from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.bse_mf_etf.models import BSEMFETFFeed


class BseMfEtfSchema(ma.ModelSchema):
    """
    Schema for loading data from bse api
    """
    class Meta:
        model = BSEMFETFFeed
        include_fk = True