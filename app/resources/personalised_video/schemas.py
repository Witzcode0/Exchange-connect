
from marshmallow import pre_dump, fields, validate

from app import ma
from app.base.schemas import default_exclude, account_fields, BaseReadArgsSchema
from app.resources.personalised_video.models import PersonalisedVideoMaster
from app.base import constants as B_VIDEO_CONST


class PersonalisedVideoSchema(ma.ModelSchema):

    class Meta:
        model = PersonalisedVideoMaster
        include_fk = True
        load_only = ('updated_by', 'created_by', '')
        dump_only = default_exclude + (
            'updated_by', 'created_by')

    file_url = ma.Url(dump_only=True)
    video_poster_url = ma.Url(dump_only=True)

    external_invitees = ma.List(ma.Nested(
        'app.resources.personalised_video_invitee.schemas.PersonalisedVideoInviteeSchema', exclude=['video_id'],
        only=['row_id','first_name', 'last_name', 'email', 'contact_no', 'video_status', 'email_status', 'video_url', 'account_id']))

    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', exclude=['child_account_ids'], only=(
            'row_id', 'account_type', 'account_name',
            'profile.profile_photo_url', 'profile.profile_thumbnail_url',
            'profile.country'), dump_only=True)

    interest_list = ma.List(ma.Nested(
        'app.resources.personalised_video_logs.schemas.PersonalisedVideoLogsSchema',exclude=['video_id'],
        only=['invitee_id', 'interest_status']), dump_only=True)


    @pre_dump(pass_many=True)
    def loads_urls(self, objs, many):
        """
        Loads the urls of invite_logo_url, invite_banner_url,
        audio_url, video_url
        """
        call_load = False  # minor optimisation
        if any(phfield in self.fields.keys() for phfield in ['file_url','filename',
                                                             'video_poster_url', 'video_poster_filename']):
            # call load urls only if the above fields are asked for
            call_load = True

        if many:  # #TODO: write optimized load_url here instead?
            for obj in objs:
                if call_load:
                    obj.load_urls()
        else:
            if call_load:
                objs.load_urls()


class PersonalisedVideoSchemaReadArgsSchema(BaseReadArgsSchema):
    account_id = fields.Integer(load_only=True)
    account_name = fields.String(load_only=True)
    video_type = fields.String(load_only=True)
