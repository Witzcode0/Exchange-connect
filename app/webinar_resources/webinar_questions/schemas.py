"""
Schemas for "webinar questions" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, webinar_fields)
from app.base import constants as APP
from app.webinar_resources.webinar_questions import (
    constants as WEBINARQUESTIONS)
from app.webinar_resources.webinar_questions.models import WebinarQuestion


class WebinarQuestionSchema(ma.ModelSchema):
    """
    Schema for loading "webinar questions" from request,
    and also formatting output
    """
    question = field_for(
        WebinarQuestion, 'question', validate=[
            validate.Length(min=1, error=APP.MSG_NON_EMPTY),
            validate.Length(max=WEBINARQUESTIONS.QUESTION_MAX_LENGTH,
                            error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = WebinarQuestion
        include_fk = True
        dump_only = default_exclude

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('webinar_api.webinarquestionapi', row_id='<row_id>'),
        'collection': ma.URLFor('webinar_api.webinarquestionlistapi')
    }, dump_only=True)

    webinar = ma.Nested(
        'app.webinar_resources.webinars.schemas.WebinarSchema',
        only=webinar_fields, dump_only=True)

    questioner = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)


class WebinarQuestionReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "webinar questions" filters from request args
    """
    question = fields.String(load_only=True)
    questioned_by = fields.Integer(load_only=True)
    webinar_id = fields.Integer(load_only=True)
