from app import db
from app.base.models import BaseModel

class PersonalisedVideoLogs(BaseModel):
    __tablename__ = 'personalised_video_logs'

    video_id = db.Column(db.Integer, db.ForeignKey('personalised_video_master.id'),
                           nullable=False)

    invitee_id = db.Column(db.Integer, db.ForeignKey('personalised_video_invitee.id'),
                           nullable=False)

    interest_status = db.Column(db.DateTime)

    #relationships
    # pr_video = db.relationship('PersonalisedVideoMaster', backref=db.backref(
    #     'interest_list', passive_deletes=True))
    invitees = db.relationship('PersonalisedVideoInvitee', backref=db.backref(
        'invitee_logs', lazy='dynamic'), foreign_keys='PersonalisedVideoLogs.invitee_id')

    def __init__(self, *args, **kwargs):
        super(PersonalisedVideoLogs, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<PersonalisedVideoLogs %r>' % (self.row_id)