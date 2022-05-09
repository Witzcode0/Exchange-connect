"""
Models for "survey responses" package.
"""

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import UniqueConstraint, CheckConstraint

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString, ChoiceString
from app.survey_resources.survey_responses import constants as SURVEYRESPONSE
from app.base import constants as APP
# related model imports done in surveys/__init__


class SurveyResponse(BaseModel):

    __tablename__ = 'survey_response'

    survey_id = db.Column(db.BigInteger, db.ForeignKey(
        'survey.id', name='survey_response_survey_id_fkey',
        ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='survey_response_user_id_fkey', ondelete="SET NULL"))
    email = db.Column(LCString(128))  # external user (future use)
    is_mail_sent = db.Column(db.Boolean, default=False)
    email_status = db.Column(ChoiceString(APP.EMAIL_STATUS_CHOICES),
        nullable=False, default=APP.EMAIL_NOT_SENT)

    first_name = db.Column(db.String(128))
    last_name = db.Column(db.String(128))
    designation = db.Column(db.String(128))
    answers = db.Column(JSONB)
    status = db.Column(ChoiceString(
        SURVEYRESPONSE.SURVEYRESPONSE_STATUS_TYPE_CHOICES),
        default=SURVEYRESPONSE.UNANSWERED)

    # multi column
    __table_args__ = (
        CheckConstraint('((user_id IS NOT NULL) OR '
                        '(email IS NOT NULL))',
                        name='c_check_srvrsp_user_id_email_not_all_null_key'),
        UniqueConstraint('survey_id', 'email',
                         name='c_survey_id_email_key'),
        UniqueConstraint('survey_id', 'user_id',
                         name='c_survey_id_user_id_key'),
    )

    # relationships
    survey = db.relationship('Survey', backref=db.backref('invites'))
    invitee = db.relationship('User', backref=db.backref(
        'survey_responses', lazy='dynamic'),
        foreign_keys='SurveyResponse.user_id')
    external_invitee = db.relationship('Survey', backref=db.backref(
        'external_invitees', lazy='dynamic', passive_deletes=True))
    invitee_j = db.relationship(
        'Survey', secondary='user',
        backref=db.backref('invited', uselist=False),
        foreign_keys='[SurveyResponse.survey_id, SurveyResponse.user_id, '
                     'SurveyResponse.email]',
        primaryjoin='Survey.row_id == SurveyResponse.survey_id',
        secondaryjoin='or_(SurveyResponse.user_id == User.row_id, '
                      'SurveyResponse.email == User.email)',
        viewonly=True)

    def __init__(self, survey_id=None, *args, **kwargs):
        self.survey_id = survey_id
        super(SurveyResponse, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<SurveyResponse %r>' % (self.survey_id)
