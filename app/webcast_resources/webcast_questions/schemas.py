"""
Schemas for "webcast questions" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, webcast_fields)
from app.base import constants as APP
from app.webcast_resources.webcast_questions import (
    constants as WEBCASTQUESTIONS)
from app.webcast_resources.webcast_questions.models import WebcastQuestion


class WebcastQuestionSchema(ma.ModelSchema):
    """
    Schema for loading "webcast questions" from request,
    and also formatting output
    """

    # default fields to exclude from the schema for speed up
    _default_exclude_fields = ['webcast_answers', ]

    question = field_for(
        WebcastQuestion, 'question', validate=[
            validate.Length(min=1, error=APP.MSG_NON_EMPTY),
            validate.Length(max=WEBCASTQUESTIONS.QUESTION_MAX_LENGTH,
                            error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = WebcastQuestion
        include_fk = True
        dump_only = default_exclude

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('webcast_api.webcastquestionapi', row_id='<row_id>'),
        'collection': ma.URLFor('webcast_api.webcastquestionlistapi')
    }, dump_only=True)

    webcast = ma.Nested(
        'app.webcast_resources.webcasts.schemas.WebcastSchema',
        dump_only=True, only=webcast_fields)

    questioner = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)


class WebcastQuestionReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "webcast questions" filters from request args
    """
    question = fields.String(load_only=True)
    questioned_by = fields.Integer(load_only=True)
    webcast_id = fields.Integer(load_only=True)
