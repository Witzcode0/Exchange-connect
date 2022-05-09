"""
Schemas for "help comments" related models
"""

from marshmallow import fields, pre_dump

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.helpdesk_resources.help_comments.models import HelpComment


class HelpCommentSchema(ma.ModelSchema):
    """
    Schema for loading "help comment" from request, and also formatting output
    """

    class Meta:
        model = HelpComment
        include_fk = True
        load_only = ('deleted', 'created_by', 'updated_by')
        dump_only = default_exclude + ('deleted', 'created_by', 'updated_by')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('helpdesk_api.helpcommentapi', row_id='<row_id>'),
        'collection': ma.URLFor('helpdesk_api.helpcommentlistapi')
    })
    ticket = ma.HyperlinkRelated(
        'helpdesk_api.helpticketapi', url_key='row_id')
    attachment_url = ma.Url()

    @pre_dump
    def loads_urls(self, obj):
        obj.load_urls()


class HelpCommentReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "help comment" filters from request args
    """
    # standard db fields
    created_by = fields.Integer(load_only=True)
    ticket_id = fields.Integer(load_only=True)
    message = fields.String(load_only=True)
