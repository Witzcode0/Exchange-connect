"""
Models for "notifications" package.
"""

from app import db
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString
from app.resources.notifications import constants as NOTIFICATION
from app.resources.posts.models import Post
from app.resources.post_stars.models import PostStar
from app.resources.post_comments.models import PostComment
from app.resources.follows.models import CFollow
from app.resources.contact_requests.models import ContactRequest
from app.corporate_access_resources.corporate_access_events.models import (
    CorporateAccessEvent)
from app.webinar_resources.webinars.models import Webinar
from app.webcast_resources.webcasts.models import Webcast
from app.toolkit_resources.project_e_meeting.models import Emeeting
from app.corporate_access_resources.ca_open_meetings.models import \
    CAOpenMeeting
from app.corporate_access_resources.ca_open_meeting_inquiries.models import \
    CAOpenMeetingInquiry
from app.survey_resources.surveys.models import Survey
from app.survey_resources.survey_responses.models import SurveyResponse
from app.resources.admin_publish_notifications.models import AdminPublishNotification
from app.toolkit_resources.projects.models import Project
from app.activity.activities.models import Activity
from app.resources.bse.models import BSEFeed
from app.resources.corporate_announcements.models import CorporateAnnouncement


class Notification(BaseModel):

    __tablename__ = 'notification'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='notification_account_id_fkey', ondelete='CASCADE'),
        nullable=False)
    user_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='notification_user_id_fkey', ondelete='CASCADE'),
        nullable=False)

    notification_group = db.Column(ChoiceString(
        NOTIFICATION.NOTIFICATION_GROUPS_CHOICES), nullable=False)
    notification_type = db.Column(ChoiceString(
        NOTIFICATION.NOTIFICATION_TYPES_CHOICES), nullable=False)
    read_time = db.Column(db.DateTime)

    # the related object ids
    # contact requests
    contact_request_id = db.Column(db.BigInteger, db.ForeignKey(
        'contact_request.id', name='notification_contact_request_id_fkey',
        ondelete='CASCADE'))
    # event invites/requests
    event_invite_request_id = db.Column(db.BigInteger, db.ForeignKey(
        'event_invite.id', name='notification_event_invite_request_id_fkey',
        ondelete='CASCADE'))
    # follows
    cfollow_id = db.Column(db.BigInteger, db.ForeignKey(
        'c_follow.id', name='notification_cfollow_id_fkey',
        ondelete='CASCADE'))
    # post id , might be required for all related
    post_id = db.Column(db.BigInteger, db.ForeignKey(
        'post.id', name='notification_post_id_fkey', ondelete='CASCADE'))
    # post comment id
    post_comment_id = db.Column(
        db.BigInteger, db.ForeignKey(
            'post_comment.id', name='notification_post_comment_id_fkey',
            ondelete='CASCADE'))
    # post star
    post_star_id = db.Column(db.BigInteger, db.ForeignKey(
        'post_star.id', name='notification_post_star_id_fkey',
        ondelete='CASCADE'))
    # surveys
    survey_id = db.Column(db.BigInteger, db.ForeignKey(
        'survey.id', name='notification_survey_id_fkey', ondelete='CASCADE'))
    corporate_access_event_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_access_event.id',
        name='notification_corporate_access_event_id_fkey',
        ondelete='CASCADE'))
    corporate_access_event_invitee_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_access_event_invitee.id',
        name='notification_ca_event_invitee_id_fkey', ondelete='CASCADE'))
    webinar_id = db.Column(db.BigInteger, db.ForeignKey(
        'webinar.id', name='notification_webinar_id_fkey',
        ondelete='CASCADE'))
    webcast_id = db.Column(db.BigInteger, db.ForeignKey(
        'webcast.id', name='notification_webcast_id_fkey',
        ondelete='CASCADE'))
    e_meeting_id = db.Column(db.BigInteger, db.ForeignKey(
        'e_meeting.id', name='notification_e_meeting_id_fkey',
        ondelete='CASCADE'))
    ca_open_meeting_id = db.Column(db.BigInteger, db.ForeignKey(
        'ca_open_meeting.id',
        name='notification_ca_open_meeting_id_fkey', ondelete='CASCADE'))
    ca_open_meeting_inquiry_id = db.Column(db.BigInteger, db.ForeignKey(
        'ca_open_meeting_inquiry.id',
        name='notification_ca_open_meeting_inquiry_id_fkey',
        ondelete='CASCADE'))
    ca_open_meeting_slot_id = db.Column(db.BigInteger, db.ForeignKey(
        'ca_open_meeting_slot.id',
        name='notification_ca_open_meeting_slot_id_fkey',
        ondelete='CASCADE'))
    caom_slot_name = db.Column(db.String(256))
    # notification from admin side to system users
    admin_publish_notification_id = db.Column(db.BigInteger, db.ForeignKey(
        'admin_publish_notification.id',
        name='notification_admin_publish_notification_id_fkey',
        ondelete='CASCADE'))

    project_id = db.Column(db.BigInteger, db.ForeignKey(
        'project.id',
        name='notification_project_id_fkey',
        ondelete='CASCADE'))
    project_status_code = db.Column(db.String(32))

    # activity
    activity_id = db.Column(db.BigInteger, db.ForeignKey(
        'activity.id',
        name="notification_activity_id_fkey",
        ondelete='CASCADE'))
    #bse announcement
    bse_id = db.Column(db.BigInteger, db.ForeignKey(
        'bse_corp_feed.id',
        name="notification_bse_id_fkey",
        ondelete='CASCADE'))
    #corporate announcement
    c_announcement_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_announcement.id',
        name="notification_c_announcement_id_fkey",
        ondelete='CASCADE'))

    # relationships
    account = db.relationship('Account', backref=db.backref(
        'notifications', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref(
        'notifications', lazy='dynamic'), foreign_keys='Notification.user_id')
    contact = db.relationship('ContactRequest', backref=db.backref(
        'notifications', lazy='dynamic'),
        foreign_keys='Notification.contact_request_id')
    cfollow = db.relationship('CFollow', backref=db.backref(
        'notifications', lazy='dynamic'),
        foreign_keys='Notification.cfollow_id')
    post_star = db.relationship('PostStar', backref=db.backref(
        'notifications', lazy='dynamic'),
        foreign_keys='Notification.post_star_id')
    post_comment = db.relationship('PostComment', backref=db.backref(
        'notifications', lazy='dynamic'),
        foreign_keys='Notification.post_comment_id')
    post = db.relationship('Post', backref=db.backref(
        'notifications', lazy='dynamic'),
        foreign_keys='Notification.post_id')
    admin_publish_notification = db.relationship(
        'AdminPublishNotification', backref=db.backref(
            'notifications', lazy='dynamic'),
        foreign_keys='Notification.admin_publish_notification_id')
    corporate_access_event = db.relationship(
        'CorporateAccessEvent', backref=db.backref(
            'notifications', lazy='dynamic'),
        foreign_keys='Notification.corporate_access_event_id')
    corporate_access_invitee = db.relationship(
        'CorporateAccessEventInvitee', backref=db.backref(
            'notifications', lazy='dynamic'),
        foreign_keys='Notification.corporate_access_event_invitee_id')
    webcast = db.relationship('Webcast', backref=db.backref(
        'notifications', lazy='dynamic'),
        foreign_keys='Notification.webcast_id')
    webinar = db.relationship('Webinar', backref=db.backref(
        'notifications', lazy='dynamic'),
        foreign_keys='Notification.webinar_id')
    e_meeting = db.relationship('Emeeting', backref=db.backref(
        'notifications', lazy='dynamic'),
        foreign_keys='Notification.e_meeting_id')
    survey = db.relationship('Survey', backref=db.backref(
        'notifications', lazy='dynamic'),
        foreign_keys='Notification.survey_id')
    ca_open_meeting = db.relationship('CAOpenMeeting', backref=db.backref(
        'notifications', lazy='dynamic'),
        foreign_keys='Notification.ca_open_meeting_id')
    ca_open_meeting_inquiry = db.relationship(
        'CAOpenMeetingInquiry', backref=db.backref(
            'notifications', cascade='all,delete', lazy='dynamic'),
        foreign_keys='Notification.ca_open_meeting_inquiry_id')
    ca_open_meeting_slot = db.relationship(
        'CAOpenMeetingSlot', backref=db.backref(
            'notifications', cascade='all,delete', lazy='dynamic'),
        foreign_keys='Notification.ca_open_meeting_slot_id')
    project = db.relationship(
        'Project', backref=db.backref(
            'notifications', cascade='all,delete', lazy='dynamic'),
        foreign_keys='Notification.project_id')

    activity = db.relationship(
        'Activity', backref=db.backref(
            'notifications', cascade="all,delete", lazy='dynamic'),
        foreign_keys='Notification.activity_id')

    bse_corp_feed = db.relationship(
        'BSEFeed', backref=db.backref(
            'notifications', cascade="all,delete", lazy='dynamic'),
        foreign_keys='Notification.bse_id')

    corporate_announcement = db.relationship(
        'CorporateAnnouncement', backref=db.backref(
            'notifications', cascade="all,delete", lazy='dynamic'),
        foreign_keys='Notification.c_announcement_id')

    def __init__(self, *args, **kwargs):
        super(Notification, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Notification row_id=%r, user_id=%r, type=%r>' % (
            self.row_id, self.user_id, self.notification_type)

    def build_message(self):
        """
        Build the notification message?
        """
        pass