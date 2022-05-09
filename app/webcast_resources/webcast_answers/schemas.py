"""
Schemas for "webcast answers" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, webcast_fields)
from app.base import constants as APP
from app.webcast_resources.webcast_answers import (
    constants as WEBCASTANSWERS)
from app.webcast_resources.webcast_answers.models import WebcastAnswer


class WebcastAnswerSchema(ma.ModelSchema):
    """
    Schema for loading "webcast answers" from request,
    and also formatting output
    """
    answer = field_for(
        WebcastAnswer, 'answer', validate=[
            validate.Length(min=1, error=APP.MSG_NON_EMPTY),
            validate.Length(max=WEBCASTANSWERS.ANSWER_MAX_LENGTH,
                            error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = WebcastAnswer
        include_fk = True
        dump_only = default_exclude

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('webcast_api.webcastanswerapi', row_id='<row_id>'),
        'collection': ma.URLFor('webcast_api.webcastanswerlistapi')
    }, dump_only=True)

    webcast = ma.Nested(
        'app.webcast_resources.webcasts.schemas.WebcastSchema',
        only=webcast_fields, dump_only=True)

    answerer = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)

    question = ma.Nested(
        'app.webcast_resources.webcast_questions.'
        'schemas.WebcastQuestionSchema',
        dump_only=True)


class WebcastAnswerReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "webcast answers" filters from request args
    """
    answer = fields.String(load_only=True)
    question_id = fields.Integer(load_only=True)
    webcast_id = fields.Integer(load_only=True)
