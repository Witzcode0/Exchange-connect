"""
Schemas for "webinar_chats" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base import constants as APP
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, webinar_fields)
from app.webinar_resources.webinar_chats.models import WebinarChatMessage
from app.webinar_resources.webinar_chats import constants as WEBCHATMSG


class WebinarChatMessageSchema(ma.ModelSchema):
    """
    Schema for loading "webinar_chat_message" from request,\
    and also formatting output
    """
    message = field_for(WebinarChatMessage, 'message', validate=[
        validate.Length(max=WEBCHATMSG.MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = WebinarChatMessage
        include_fk = True
        dump_only = default_exclude + ('sent_by',)

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor(
            'webinar_api.webinarchatmessageapi', row_id='<row_id>'),
        'collection': ma.URLFor('webinar_api.webinarchatmessagelistapi')
    }, dump_only=True)

    webinar = ma.Nested(
        'app.webinar_resources.webinars.schemas.WebinarSchema',
        only=webinar_fields, dump_only=True)

    sender = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)


class WebinarChatMessageReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "webinar_chat_message" filters from request args
    """
    webinar_id = fields.Integer(load_only=True)
    sent_by = fields.Integer(load_only=True)
