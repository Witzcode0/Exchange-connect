"""
Schemas for "survey responses" related models
"""

from marshmallow import fields, validate, validates_schema, ValidationError
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base import constants as APP
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.survey_resources.survey_responses.models import SurveyResponse
from app.survey_resources.survey_responses import constants as SURVEYRESPONSE


class SurveyResponseSchema(ma.ModelSchema):
    """
    Schema for loading "SurveyResponse" and also formatting output
    """

    email = field_for(
        SurveyResponse, 'email', field_class=fields.Email,
        validate=[validate.Length(max=SURVEYRESPONSE.INVITEE_EMAIL_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])
    status = field_for(SurveyResponse, 'status', validate=validate.OneOf(
        SURVEYRESPONSE.SURVEYRESPONSE_STATUS_TYPES))
    answers = field_for(SurveyResponse, 'answers', field_class=fields.Dict)

    class Meta:
        model = SurveyResponse
        include_fk = True
        load_only = ('updated_by', 'created_by')
        dump_only = default_exclude + ('updated_by', 'created_by',
                    'is_mail_sent','email_status')
        exclude = ('invitee_j', )

    links = ma.Hyperlinks({
        'self': ma.URLFor('api.surveyresponseapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.surveyresponselistapi')
    }, dump_only=True)

    invitee = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)

    @validates_schema
    def validate_survey_invitee_users(self, data):
        """
        Multiple validation checks for user_id, email, first_name, last_name
        and designation
        """
        error_args = []
        if 'user_id' not in data and 'email' not in data:
            error_args = [APP.MSG_NON_EMPTY, 'user_id, email']

        if 'user_id' in data and 'email' in data:
            error_args = ['Both user_id and email' +
                          ' should not be there', 'user_id, email']

        if ('user_id' in data and data['user_id'] and (
                ('first_name' in data and data['first_name']) or
                ('last_name' in data and data['last_name']) or
                ('designation' in data and data['designation']))):
            error_args = [
                'If user_id is given, first_name, ' +
                'last_name and designation ' + 'should not be there',
                'user_id, first_name, last_name, designation']

        if error_args:
            raise ValidationError(*error_args)


class SurveyResponseReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "SurveyResponse" filters from request args
    """
    survey_id = fields.Integer(load_only=True)
    answers = fields.String(load_only=True)
    status = fields.String(load_only=True, validate=validate.OneOf(
        SURVEYRESPONSE.SURVEYRESPONSE_STATUS_TYPES))
