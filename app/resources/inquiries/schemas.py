"""
Schemas for "inquiries" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base import constants as APP
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, account_fields)
from app.resources.inquiries.models import Inquiry
from app.resources.inquiries import constants as INQUIRY


class InquirySchema(ma.ModelSchema):
    """
    Schema for loading "inquiries" from requests, and also formatting output
    """

    name = field_for(Inquiry, 'name', validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=INQUIRY.NAME_EMAIL_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    email = field_for(Inquiry, 'email', field_class=fields.Email, validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=INQUIRY.NAME_EMAIL_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    contact_number = field_for(Inquiry, 'contact_number', validate=[
        validate.Length(max=INQUIRY.CONTACT_NUMBER_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    message = field_for(Inquiry, 'message', validate=[
        validate.Length(max=INQUIRY.MESSAGE_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    remarks = field_for(Inquiry, 'remarks', validate=[
        validate.Length(max=INQUIRY.REMARKS_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    subject = field_for(Inquiry, 'subject', validate=[
        validate.Length(max=INQUIRY.SUBJECT_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    inquiry_type = field_for(Inquiry, 'inquiry_type', validate=validate.OneOf(
        INQUIRY.INQ_TYPE_TYPES))
    major_sub_type = field_for(
        Inquiry, 'major_sub_type', validate=validate.OneOf(
            INQUIRY.INQT_PLQ_TYPES), allow_none=True)

    class Meta:
        model = Inquiry
        include_fk = True
        load_only = ('updated_by', 'created_by', 'account_id')
        dump_only = default_exclude + (
            'updated_by', 'created_by', 'account_id', 'domain_id')

    links = ma.Hyperlinks({
        'self': ma.URLFor('api.inquiryapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.inquirylistapi')
    }, dump_only=True)

    editor = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True)


class InquiryContactUsSchema(InquirySchema):
    """
    Schema for contact us inquiry type
    """
    inquiry_type = fields.Constant(INQUIRY.INQT_CONTACT)


class InquiryPlanSchema(InquirySchema):
    """
    Schema for plan quote inquiry type
    """
    inquiry_type = fields.Constant(INQUIRY.INQT_PLAN_QUOTE)
    major_sub_type = fields.String(required=True, validate=validate.OneOf(
        INQUIRY.INQT_PLQ_TYPES))

    class Meta:
        model = Inquiry
        include_fk = True
        load_only = ('updated_by', 'created_by', 'account_id')
        dump_only = default_exclude + (
            'updated_by', 'created_by', 'account_id', 'name', 'email',
            'domain_id')


class InquiryReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "inquiries" filters from request args
    """
    name = fields.String(load_only=True)
    email = fields.String(load_only=True)
    created_by = fields.Integer(load_only=True)
    inquiry_type = fields.String(load_only=True, validate=validate.OneOf(
        INQUIRY.INQ_TYPE_TYPES))
    major_sub_type = fields.String(load_only=True, validate=validate.OneOf(
        INQUIRY.INQT_PLQ_TYPES))
