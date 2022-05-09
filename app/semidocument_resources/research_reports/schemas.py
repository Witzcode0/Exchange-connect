"""
Schemas for "corporate announcement" related models
"""

from flask import request
from marshmallow import (
    fields, pre_dump, validates_schema, ValidationError)
from marshmallow_sqlalchemy import field_for
from sqlalchemy.orm import load_only

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, account_fields)
from app.resources.accounts import constants as ACCT
from app.resources.accounts.models import Account
from app.semidocument_resources.research_reports.models import ResearchReport
from app.resources.corporate_announcements.models import CorporateAnnouncement
from app.semidocument_resources.research_report_parameters.models import (
    ResearchReportParameter)

# files details that will be passed while populating user relation
corporate_user_fields = user_fields + [
    'account.profile.profile_photo_url',
    'account.profile.profile_thumbnail_url', 'account.identifier']
corporate_account_fields = account_fields + [
    'profile.profile_photo_url', 'profile.profile_thumbnail_url',
    'identifier']


class ResearchReportSchema(ma.ModelSchema):
    """
    Schema for loading "ResearchReport" from request, and also
    formatting output
    """
    _fields_for_xml = ['row_id', 'subject', 'parameters', 'corporate_account']

    subject = field_for(
        ResearchReport, 'subject', required=True)

    class Meta:
        model = ResearchReport
        include_fk = True
        load_only = ('deleted', 'account_id', 'updated_by', 'created_by')
        dump_only = default_exclude + (
            'account_id', 'updated_by', 'deleted', 'created_by',
            'research_report_date')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('semi_documentation_api.researchreportapi', row_id='<row_id>'),
        'collection': ma.URLFor('semi_documentation_api.researchreportlistapi')
    }, dump_only=True)

    file_url = ma.Url(dump_only=True)
    thumbnail_url = ma.Url(dump_only=True)
    xml_file_url = ma.Url(dump_only=True)
    announcement_ids = fields.List(fields.Integer(), dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=corporate_user_fields,
        dump_only=True)
    editor = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=corporate_user_fields,
        dump_only=True)
    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema',
        only=corporate_account_fields,
        dump_only=True)
    corporate_account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema',
        only=corporate_account_fields,
        dump_only=True)
    announcements = ma.List(ma.Nested(
        'app.resources.corporate_announcements.schemas.'
        'CorporateAnnouncementSchema', only=[
            'row_id', 'subject', 'url', 'file_url']), dump_only=True)
    parameters = ma.List(ma.Nested(
        'app.semidocument_resources.research_report_parameters.schemas.'
        'ResearchReportParameterSchema', only=[
            'row_id', 'account_id', 'parameter_name', 'description',
            'edited_description', 'sequence']))
    _cached_announcements = None

    @pre_dump(pass_many=True)
    def loads_urls(self, objs, many):
        """
        Loads the url of file
        """
        call_load = False  # minor optimisation
        if any(phfield in self.fields.keys() for phfield in [
                'file_url', 'file']):
            # call load urls only if the above fields are asked for
            call_load = True

        if many:  # #TODO: write optimized load_url here instead?
            for obj in objs:
                if call_load:
                    obj.load_urls()
        else:
            if call_load:
                objs.load_urls()

    @validates_schema
    def validate_file_and_url(self, data):
        """
        Validate that file and url both should not be there in data
        """
        error = False
        if 'subject' in data and not data['subject']:
            raise ValidationError('Subject can not be blank')

        # validating that account_id is "sell-side" and corporate_account_id
        # is of type "corporate"

        if 'corporate_account_id' in data and data['corporate_account_id']:
            account = Account.query.get(data['corporate_account_id'])
            if account and account.account_type != ACCT.ACCT_CORPORATE:
                raise ValidationError('Research report can be created only' 
                    'for corporate accounts')

        if 'account_id' in data and data['account_id']:
            account = Account.query.get(data['account_id'])
            if account and account.account_type != ACCT.ACCT_SELL_SIDE_ANALYST:
                raise ValidationError('Research report can be created only'
                                      ' by sell-side accounts')

    @validates_schema(pass_original=True)
    def validate_announcement_ids(self, data, original_data):
        """
        Validate announcement exists or not
        :param data:
        :param original_data:
        :return:
        """
        # file exists or not
        self._cached_announcements = []
        missing_announcements = []
        error = False
        ann_ids = []

        if ('announcement_ids' in original_data and
                original_data['announcement_ids']):
            ann_ids = original_data['announcement_ids'][:]
        # validate file_ids, and load all the _cached_files
        if ann_ids:
            # make query
            anids = []
            for f in ann_ids:
                try:
                    anids.append(int(f))
                except Exception as e:
                    continue
            self._cached_announcements = [
                f for f in CorporateAnnouncement.query.filter(
                    CorporateAnnouncement.row_id.in_(anids)).options(
                    load_only('row_id', 'deleted')).all() if not f.deleted]
            ann_ids = [f.row_id for f in self._cached_announcements]
            missing_announcements = set(anids) - set(ann_ids)
            if missing_announcements:
                error = True

        if error:
            raise ValidationError(
                'Announcements: %s do not exist' % missing_announcements,
                'announcement_ids')

    @validates_schema(pass_original=True)
    def validate_report_parameters(self, data, original_data):
        """
        Validate research report parameter exists or not
        :param data:
        :param original_data:
        :return:
        """
        # file exists or not
        self._cached_report_params = []
        self._report_param_id_vs_object = {}
        report_parameters = []

        if ('report_parameters' in original_data and
                original_data['report_parameters']):
            report_parameters = original_data['report_parameters'][:]
        # validate file_ids, and load all the _cached_files
        if report_parameters:
            param_names = [x['parameter_name'] for x in report_parameters]
            self._cached_report_params = [
                f for f in ResearchReportParameter.query.filter(
                    ResearchReportParameter.parameter_name.in_(param_names),
                    ResearchReportParameter.account_id ==
                    data['corporate_account_id']).options(
                    load_only('row_id', 'parameter_name')).all()]
            found_param_names = [f.parameter_name for f in
                                 self._cached_report_params]
            missing_parameters = set(param_names) - set(found_param_names)
            if missing_parameters:
                raise ValidationError(
                    'Parameters: {} do not exist for account_id :{}'.format(
                        missing_parameters, data['corporate_account_id']))


class AdminResearchReportSchema(ResearchReportSchema):
    """
    Schema for loading "ResearchReportSchema" from request for Admin, and also
    formatting output
    """

    class Meta:
        model = ResearchReport
        include_fk = True
        load_only = ('deleted', 'updated_by', 'created_by')
        dump_only = default_exclude + ('updated_by', 'deleted', 'created_by')


class ResearchReportReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "ResearchReport" filters from request args
    """
    # standard db fields
    subject = fields.String(load_only=True)
    description = fields.String(load_only=True)
    corporate_account_id = fields.String(load_only=True)
    account_id = fields.String(load_only=True)
    company_name = fields.String(load_only=True)
    main_filter = fields.String(load_only=True)
