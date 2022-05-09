"""
Schemas for "crm distribution list" related models
"""

from marshmallow import (
    fields, pre_dump, validates_schema, ValidationError)
from sqlalchemy.orm import load_only

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.crm_resources.crm_distribution_lists.models import CRMDistributionList
from app.crm_resources.crm_distribution_file_library.models import (
    CRMDistributionLibraryFile)


class CRMDistAttachmentFileSizeSchema(ma.Schema):
    """
    Schema for attachment name with file size
    """
    attachment_name = fields.String(dump_only=True)
    size = fields.Integer(dump_only=True)


class CRMDistributionListSchema(ma.ModelSchema):
    """
    Schema for loading "crm distribution list" from request,
    and also formatting output
    """
    _default_exclude_fields = [
        'attachment_urls', 'file_attachment_size', 'html_files',
        'html_template', 'attachments']
    _cached_files = None
    html_file_ids = fields.List(fields.Integer(), dump_only=True)

    class Meta:
        model = CRMDistributionList
        include_fk = True
        load_only = ('updated_by', 'account_id', 'created_by')
        dump_only = default_exclude + (
            'updated_by', 'account_id', 'created_by')

    attachment_urls = ma.List(ma.Url(dump_only=True))
    file_attachment_size = ma.List(ma.Nested(
        CRMDistAttachmentFileSizeSchema, dump_only=True))

    crm_distribution_invitees = ma.List(ma.Nested(
        'app.crm_resources.crm_distribution_invitee_lists.schemas.'
        'CRMDistributionInviteeListSchema', exclude=['distribution_list_id'],
        only=['row_id', 'invitee_email', 'invitee_first_name',
              'invitee_last_name', 'is_mail_sent', 'user_id', 'user',
              'email_status', 'sent_on']))
    html_files = ma.List(ma.Nested(
        'app.crm_resources.crm_distribution_file_library.schemas.'
        'CRMDistributionLibraryFileSchema', only=[
            'row_id', 'file_url', 'filename']),
        dump_only=True)

    @pre_dump(pass_many=True)
    def loads_urls(self, objs, many):
        """
        Loads the urls of invite_logo_url, invite_banner_url,
        audio_url, video_url
        """
        if many:  # #TODO: write optimized load_url here instead?
            pass
        else:
            objs.load_urls()

    @validates_schema(pass_original=True)
    def validate_file_ids(self, data, original_data):
        """
        Validate file ids exists or not
        :param data:
        :param original_data:
        :return:
        """

        # file exists or not
        self._cached_files = []
        missing_files = []
        error_files = False
        # load all the file ids
        f_ids = []
        if 'html_file_ids' in original_data and original_data['html_file_ids']:
            f_ids = original_data['html_file_ids'][:]
        # validate file_ids, and load all the _cached_files
        if f_ids:
            # make query
            fids = []
            for f in f_ids:
                try:
                    fids.append(int(f))
                except Exception as e:
                    continue
            self._cached_files = [
                f for f in CRMDistributionLibraryFile.query.filter(
                    CRMDistributionLibraryFile.row_id.in_(fids)).options(
                    load_only('row_id')).all()]
            file_ids = [f.row_id for f in self._cached_files]
            missing_files = set(fids) - set(file_ids)
            if missing_files:
                error_files = True

        if error_files:
            raise ValidationError(
                'Files: %s do not exist' % missing_files,
                'html_file_ids'
            )


class CRMDistributionGetListSchema(CRMDistributionListSchema):
    """
    Schema for loading "crm distribution get list" from request,
    and also formatting output
    """
    crm_distribution_invitees = ma.List(ma.Nested(
        'app.crm_resources.crm_distribution_invitee_lists.schemas.'
        'CRMDistributionInviteeListSchema', exclude=['distribution_list_id'],
        only=['row_id', 'invitee_email', 'invitee_first_name',
              'invitee_last_name', 'is_mail_sent']))


class CRMDistributionListReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "CRMDistribution List" filters from request args
    """

    campaign_name = fields.String(load_only=True)
    is_draft = fields.String(load_only=True)
