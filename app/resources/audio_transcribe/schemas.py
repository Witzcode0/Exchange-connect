from marshmallow import pre_dump, fields

from app import ma
from app.resources.audio_transcribe.models import AudioTranscribe
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.base.schemas import account_fields

corporate_account_fields = account_fields + [
    'profile.profile_photo_url', 'profile.profile_thumbnail_url',
    'identifier']

class AudioTranscribeSchema(ma.ModelSchema):

    class Meta:
        model = AudioTranscribe
        include_fk = True
        load_only = ('updated_by', 'created_by', 'err_msg', 'transcript_job_name')
        dump_only = default_exclude + (
            'updated_by', 'created_by', 'transcript_job_name')

    file_url = ma.Url(dump_only=True)
    transcript_url = ma.Url(dump_only=True)

    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema',
        only=account_fields,
        dump_only=True)

    @pre_dump(pass_many=True)
    def loads_urls(self, objs, many):
        """
        Loads the urls of invite_logo_url, invite_banner_url,
        audio_url, video_url
        """
        call_load = False  # minor optimisation
        if any(phfield in self.fields.keys() for phfield in ['file_url', 'filename', 'title', 'transcript_url']):
            # call load urls only if the above fields are asked for
            call_load = True

        if many:  # #TODO: write optimized load_url here instead?
            for obj in objs:
                if call_load:
                    obj.load_urls()
        else:
            if call_load:
                objs.load_urls()


class AudioTranscribeReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "transcription jobs" filters from request args
    """
    title = fields.String(load_only=True)
    email = fields.String(load_only=True)
    account_name = fields.String(load_only=True)