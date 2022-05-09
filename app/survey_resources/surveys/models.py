"""
Models for "surveys" package.
"""

from sqlalchemy.dialects.postgresql import JSONB, ARRAY

from app import db
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString, LCString
from app.survey_resources.surveys import constants as SURVEY
from app.survey_resources.survey_responses import constants as SURVEY_RESPONSE
# related model imports done in surveys/__init__


class Survey(BaseModel):

    __tablename__ = 'survey'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='survey_account_id_fkey', ondelete='CASCADE'),
        nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='survey_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='survey_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)

    title = db.Column(db.String(512), nullable=False)
    agenda = db.Column(db.String(9216))

    # invite related
    invite_text = db.Column(db.String(4096))
    welcome_message = db.Column(db.String(512))
    success_message = db.Column(db.String(512))

    questions = db.Column(JSONB)
    status = db.Column(ChoiceString(SURVEY.SURVEY_STATUS_TYPE_CHOICES),
                       default=SURVEY.OPEN)
    editable = db.Column(db.Boolean, default=True)
    started_at = db.Column(db.DateTime)
    ended_at = db.Column(db.DateTime)
    # to check if currently sending emails to invitees in background
    is_in_process = db.Column(db.Boolean, default=False)
    # to check if creator already got the mail or not , creator will not get
    # email on resend mail
    creator_mail_sent = db.Column(db.Boolean, default=False)

    cc_emails = db.Column(ARRAY(LCString(128)))  # for emails

    # relationships
    account = db.relationship('Account', backref=db.backref(
        'survey', lazy='dynamic'), foreign_keys='Survey.account_id')
    creator = db.relationship('User', backref=db.backref(
        'survey', lazy='dynamic'), foreign_keys='Survey.created_by')
    invitees = db.relationship(
        'User', secondary='survey_response', backref=db.backref(
            'surveys_invited', lazy='dynamic'),
        foreign_keys='[SurveyResponse.survey_id, SurveyResponse.user_id]',
        passive_deletes=True, viewonly=True)
    respondents = db.relationship(
        'SurveyResponse', backref=db.backref(
            'survey_responded', lazy='dynamic', uselist=True),
        foreign_keys='[SurveyResponse.survey_id]',
        primaryjoin="and_(SurveyResponse.status == '" +
        SURVEY_RESPONSE.ANSWERED +
        "', SurveyResponse.survey_id == Survey.row_id)", viewonly=True)
    non_respondents = db.relationship(
        'SurveyResponse', backref=db.backref(
            'survey_not_responded', lazy='dynamic', uselist=True),
        foreign_keys='[SurveyResponse.survey_id]',
        primaryjoin="and_(SurveyResponse.status == '" +
        SURVEY_RESPONSE.UNANSWERED +
        "', SurveyResponse.survey_id == Survey.row_id)", viewonly=True)

    # dynamic properties
    responded = 0
    not_responded = 0

    def __init__(self, title=None, *args, **kwargs):
        self.title = title
        super(Survey, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Survey %r>' % (self.title)
