"""
Schemas for "webinar answers" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, webinar_fields)
from app.base import constants as APP
from app.webinar_resources.webinar_answers import (
    constants as WEBINARANSWERS)
from app.webinar_resources.webinar_answers.models import WebinarAnswer


class WebinarAnswerSchema(ma.ModelSchema):
    """
    Schema for loading "webinar answers" from request,
    and also formatting output
    """
    answer = field_for(
        WebinarAnswer, 'answer', validate=[
            validate.Length(min=1, error=APP.MSG_NON_EMPTY),
            validate.Length(max=WEBINARANSWERS.ANSWER_MAX_LENGTH,
                            error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = WebinarAnswer
        include_fk = True
        dump_only = default_exclude

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('webinar_api.webinaranswerapi', row_id='<row_id>'),
        'collection': ma.URLFor('webinar_api.webinaranswerlistapi')
    }, dump_only=True)

    webinar = ma.Nested(
        'app.webinar_resources.webinars.schemas.WebinarSchema',
        only=webinar_fields, dump_only=True)

    answerer = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)

    question = ma.Nested(
        'app.webinar_resources.webinar_questions.'
        'schemas.WebinarQuestionSchema',
        dump_only=True)


class WebinarAnswerReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "webinar answers" filters from request args
    """
    answer = fields.String(load_only=True)
    question_id = fields.Integer(load_only=True)
    webinar_id = fields.Integer(load_only=True)
