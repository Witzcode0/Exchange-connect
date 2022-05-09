from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString
from app.base.model_fields import ChoiceString
from app.resources.personalised_video_invitee import constants as PVSTATUS
from app.resources.personalised_video.models import PersonalisedVideoMaster


class PersonalisedVideoInvitee(BaseModel):
    __tablename__ = 'personalised_video_invitee'

    created_by = db.Column(db.Integer, db.ForeignKey('user.id'),
                           nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'),
                           nullable=False)

    video_id = db.Column(db.Integer, db.ForeignKey('personalised_video_master.id'),
                           nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'),
                           nullable=False)
    first_name = db.Column(db.String(128))
    last_name = db.Column(db.String(128))
    email = db.Column(LCString(128), nullable=False)
    contact_no = db.Column(db.String(50))
    email_status = db.Column(db.Boolean, default=False)
    video_status = db.Column(ChoiceString(PVSTATUS.PV_STATUS_TYPE_CHOICES),
                             nullable=False, default=PVSTATUS.PVSTATUS_PENDING)
    video_url = db.Column(db.String(256))
    parent_id = db.Column(db.Integer)

    # relationships
    # pr_video_invitees = db.relationship('PersonalisedVideoMaster', backref=db.backref(
    #     'external_invitees', lazy='dynamic', passive_deletes=True))
    pr_video_invitees = db.relationship('PersonalisedVideoMaster', backref=db.backref(
            'external_invitees', passive_deletes=True))

    def __init__(self, created_by=None, updated_by=None,
                 video_id=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        self.video_id = video_id
        super(PersonalisedVideoInvitee, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<PersonalisedVideoInvitee %r>' % (self.row_id)