from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.personalised_video_invitee.models import PersonalisedVideoInvitee


class PersonalisedVideoInviteeSchema(ma.ModelSchema):
    class Meta:
        model = PersonalisedVideoInvitee
        include_fk = True
        load_only = ('updated_by', 'created_by')
        dump_only = default_exclude + (
            'updated_by', 'created_by')

    pr_video = ma.Nested('app.resources.personalised_video.schemas.PersonalisedVideoSchema',
                         only=['row_id', 'filename', 'video_type'], dump_only=True)
