from marshmallow import fields

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.personalised_video_logs.models import PersonalisedVideoLogs


class PersonalisedVideoLogsSchema(ma.ModelSchema):
    class Meta:
        model = PersonalisedVideoLogs
        include_fk = True
        load_only = ('updated_by', 'created_by')
        dump_only = default_exclude + (
            'updated_by', 'created_by')

    invitees = ma.Nested('app.resources.personalised_video_invitee.schemas.PersonalisedVideoInviteeSchema',
                         only=['row_id','video_id','first_name','last_name','email'], dump_only=True)


class PersonalisedVideoLogsReadArgsSchema(BaseReadArgsSchema):
    invitee_id = fields.Integer(load_only=True, required=True)