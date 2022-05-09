"""
Schemas for "surveys" related models
"""

from marshmallow import (
    fields, validate, validates_schema, ValidationError, pre_dump, pre_load)
from marshmallow_sqlalchemy import field_for
from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload
from flask import g

from app import ma
from app.base import constants as APP
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, account_fields)
from app.survey_resources.surveys.models import Survey
from app.survey_resources.surveys import constants as SURVEY
from app.resources.contacts.models import Contact
from app.resources.users.models import User


survey_invite_fields = ['row_id', 'status', 'links', 'created_date',
                        'email', 'first_name', 'last_name', 'designation',
                        'user_id', 'email', 'first_name', 'last_name',
                        'designation', 'invitee','is_mail_sent','email_status']

# account details that will be passed while populating account relation
creator_user_fields = user_fields + ['account.profile.profile_thumbnail_url']


class SurveySchema(ma.ModelSchema):
    """
    Schema for loading "Survey" from requests, and also formatting output
    """

    # default fields to exclude from the schema for speed up
    _default_exclude_fields = ['respondents', 'non_respondents', 'invitees',
                               'creator_mail_sent']

    title = field_for(Survey, 'title', validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=SURVEY.TITLE_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    status = field_for(Survey, 'status', validate=validate.OneOf(
        SURVEY.SURVEY_STATUS_TYPES))
    questions = field_for(Survey, 'questions', field_class=fields.Dict)
    cc_emails = fields.List(fields.Email(), allow_none=True)
    invitee_ids = fields.List(fields.Integer(), dump_only=True)
    email_ids = fields.List(fields.Email(), dump_only=True)
    _cached_contact_users = None
    _cached_emails = None
    # counts of responded, not responded
    responded = fields.Integer(dump_only=True)
    not_responded = fields.Integer(dump_only=True)

    class Meta:
        model = Survey
        include_fk = True
        load_only = ('account_id', 'updated_by', 'created_by',
                     'external_invitees')
        dump_only = default_exclude + ('account_id', 'updated_by',
                                       'created_by')

    links = ma.Hyperlinks({
        'self': ma.URLFor('api.surveyapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.surveylistapi')
    }, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=creator_user_fields,
        dump_only=True)
    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True)
    invites = ma.List(ma.Nested(
        'app.survey_resources.survey_responses.'
        'schemas.SurveyResponseSchema',
        only=survey_invite_fields, dump_only=True))
    invited = ma.Nested(
        'app.survey_resources.survey_responses.'
        'schemas.SurveyResponseSchema',
        only=survey_invite_fields, dump_only=True)
    # add survey invites nested field
    invitees = ma.List(ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True))
    respondents = ma.List(ma.Nested(
        'app.survey_resources.survey_responses.'
        'schemas.SurveyResponseSchema',
        only=survey_invite_fields, dump_only=True))
    non_respondents = ma.List(ma.Nested(
        'app.survey_resources.survey_responses.'
        'schemas.SurveyResponseSchema',
        only=survey_invite_fields, dump_only=True))
    external_invitees = ma.List(ma.Nested(
        'app.survey_resources.survey_responses.'
        'schemas.SurveyResponseSchema', exclude=['user_id'],
        only=['row_id', 'email', 'first_name', 'last_name', 'designation',
              'invitee']))

    @validates_schema(pass_original=True)
    def validate_invitee_ids(self, data, original_data):
        """
        Validate that the invitee_ids users (contacts) exist, and are contacts,
        these can be passed as part of survey
        """
        error = False
        missing = []
        self._cached_contact_users = []
        eids = []
        if 'invitee_ids' in original_data and original_data['invitee_ids']:
            eids = original_data['invitee_ids'][:]
        # validate user_ids, and load all the _cached_contact_users
        if eids:
            # make query
            iids = []
            for iid in eids:
                try:
                    iids.append(int(iid))
                except Exception as e:
                    continue
            query = Contact.query.filter(or_(
                and_(Contact.sent_by.in_(iids), Contact.sent_to ==
                     g.current_user['row_id']),
                and_(Contact.sent_to.in_(iids), Contact.sent_by ==
                     g.current_user['row_id']))).options(
                # sendee and related stuff
                joinedload(Contact.sendee).load_only('row_id').joinedload(
                    User.profile),
                # sender and related stuff
                joinedload(Contact.sender).load_only('row_id').joinedload(
                    User.profile))

            invitee_ids = []  # for validating missing (incorrect user ids)
            for c in query.all():
                the_contact = c.sender if c.sent_to ==\
                    g.current_user['row_id'] else c.sendee
                self._cached_contact_users.append(the_contact)
                invitee_ids.append(the_contact.row_id)

            missing = set(iids) - set(invitee_ids)
            if missing:
                error = True

        if error:
            raise ValidationError(
                'Contacts: %s do not exist' % missing,
                'invitee_ids'
            )

    @validates_schema(pass_original=True)
    def validate_email_ids(self, data, original_data):
        """
        Validate email ids
        """
        self._cached_emails = []
        emids = []
        if 'email_ids' in original_data and original_data['email_ids']:
            emids = original_data['email_ids'][:]

        # validate email_ids, and load all the _cached_emails
        if emids:
            for e in original_data['email_ids']:
                try:
                    self._cached_emails.append(e)
                except Exception as e:
                    continue

    @pre_dump(pass_many=True)
    def loads_counts(self, objs, many):
        """
        Loads the counts of responded, not responded
        """
        call_load = False  # minor optimisation
        if any(phfield in self.fields.keys() for phfield in [
                'responded', 'not_responded']):
            # call load urls only if the above fields are asked for
            call_load = True

        if many:
            if call_load:
                for obj in objs:
                    obj.responded = len(obj.respondents)
                    obj.not_responded = len(obj.non_respondents)
        else:
            if call_load:
                objs.responded = len(objs.respondents)
                objs.not_responded = len(objs.non_respondents)

    @pre_load(pass_many=True)
    def cc_emails_none_conversion(self, objs, many):
        """
        convert cc_emails into None if empty list and Null
        """
        if 'cc_emails' in objs and (
                not objs['cc_emails'] or objs['cc_emails'] == []):
            objs['cc_emails'] = None


class SurveyReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "Survey" filters from request args
    """

    title = fields.String(load_only=True)
    status = fields.String(load_only=True, validate=validate.OneOf(
        SURVEY.SURVEY_STATUS_TYPES))
    editable = fields.Boolean(load_only=True)
