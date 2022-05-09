"""
Schemas for "helptickets" related models
"""

from marshmallow import fields, validate, pre_dump
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.helpdesk_resources.help_tickets import constants as HTICKET
from app.helpdesk_resources.help_tickets.models import HelpTicket
from app.base import constants as APP


class HelpTicketSchema(ma.ModelSchema):
    """
    Schema for loading "help ticket" from request, and also formatting output
    """
    # as these are custom db fields, they require extra validator
    section = field_for(HelpTicket, 'section', validate=validate.OneOf(
        HTICKET.SECTION_TYPES))
    function = field_for(HelpTicket, 'function', validate=validate.OneOf(
        HTICKET.FUNCTION_TYPES))
    status = field_for(HelpTicket, 'status', validate=validate.OneOf(
        HTICKET.STATUS_TYPES))

    name = field_for(HelpTicket, 'name', validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=HTICKET.NAME_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    email = field_for(HelpTicket, 'email', field_class=fields.Email, validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=HTICKET.EMAIL_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    phone = field_for(HelpTicket, 'phone', validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=HTICKET.PHONE_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    subject = field_for(HelpTicket, 'subject', validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=HTICKET.SUBJECT_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    description = field_for(HelpTicket, 'description', validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=HTICKET.DES_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = HelpTicket
        include_fk = True
        load_only = ('deleted', 'created_by', 'updated_by')
        dump_only = default_exclude + (
            'deleted', 'created_by', 'updated_by', 'domain_id')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('helpdesk_api.helpticketapi', row_id='<row_id>'),
        'collection': ma.URLFor('helpdesk_api.helpticketlistapi')
    })
    attachment_url = ma.Url()
    # format the comments as list of links
    comments = ma.List(ma.HyperlinkRelated(
        'helpdesk_api.helpcommentapi', url_key='row_id'))
    # also add an all_comments field
    all_comments = ma.URLFor(
        'helpdesk_api.helpcommentlistapi', ticket_id='<row_id>')

    @pre_dump
    def loads_urls(self, obj):
        obj.load_urls()


class HelpTicketReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "help ticket" filters from request args
    """
    # standard db fields
    created_by = fields.Integer(load_only=True)
    name = fields.String(load_only=True)
    email = fields.String(load_only=True)
    phone = fields.String(load_only=True)
    section = fields.String(
        load_only=True, validate=validate.OneOf(HTICKET.SECTION_TYPES))
    function = fields.String(
        load_only=True, validate=validate.OneOf(HTICKET.FUNCTION_TYPES))
    subject = fields.String(load_only=True)
    status = fields.String(
        load_only=True, validate=validate.OneOf(HTICKET.STATUS_TYPES))
    assignee_id = fields.Integer(load_only=True)
