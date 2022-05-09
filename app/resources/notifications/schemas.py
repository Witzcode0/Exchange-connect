"""
Schemas for "notifications" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, account_fields)
from app.resources.notifications.models import Notification
from app.resources.notifications import constants as NOTIFY


# files details that will be passed while populating user relation
file_fields = ['row_id', 'filename', 'file_type', 'file_url']
post_fields = ['row_id', 'title', 'description']


class NotificationSchema(ma.ModelSchema):
    """
    Schema for formatting output
    """
    notification_group = field_for(
        Notification, 'notification_group',
        validate=validate.OneOf(NOTIFY.NOTIFICATION_GROUPS))
    notification_type = field_for(
        Notification, 'notification_type',
        validate=validate.OneOf(NOTIFY.NOTIFICATION_TYPES))

    class Meta:
        model = Notification
        include_fk = True
        dump_only = default_exclude

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.notificationapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.notificationlistapi')
    }, dump_only=True)
    # #TODO: maybe implement in future, if required
    # message = fields.String(dump_only=True)
    user = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True)
    post = ma.Nested(
        'app.resources.posts.schemas.PostSchema', only=[
            'row_id', 'title', 'description'], dump_only=True)
    post_comment = ma.Nested(
        'app.resources.post_comments.schemas.PostCommentSchema',
        dump_only=True)
    post_star = ma.Nested(
        'app.resources.post_stars.schemas.PostStarSchema', dump_only=True)
    cfollow = ma.Nested(
        'app.resources.follows.schemas.CFollowSchema', only=[
            'company', 'follower'], dump_only=True)
    contact = ma.Nested(
        'app.resources.contact_requests.schemas.ContactRequestSchema',
        only=['the_other', 'sender', 'sendee'], dump_only=True)
    corporate_access_event = ma.Nested(
        'app.corporate_access_resources.corporate_access_events.schemas'
        '.CorporateAccessEventSchema', only=[
            'row_id', 'creator', 'title', 'event_type_id',
            'event_sub_type_id', 'started_at', 'ended_at'], dump_only=True)
    corporate_access_invitee = ma.Nested(
        'app.corporate_access_resources.corporate_access_event_invitees.'
        'schemas.CorporateAccessEventInviteeSchema', only=[
            'invitee', 'corporate_access_event', 'invitee_first_name',
            'invitee_last_name', 'invitee_email'], dump_only=True)
    webcast = ma.Nested(
        'app.webcast_resources.webcasts.schemas.WebcastSchema',
        only=['row_id', 'creator', 'title', 'description',
              'started_at', 'ended_at'], dump_only=True)
    webinar = ma.Nested(
        'app.webinar_resources.webinars.schemas.WebinarSchema',
        only=['row_id', 'creator', 'title', 'description',
              'started_at', 'ended_at'], dump_only=True)
    e_meeting = ma.Nested(
        'app.toolkit_resources.project_e_meeting.schemas.EMeetingSchema',
        only=['row_id', 'creator', 'meeting_subject', 'meeting_agenda',
              'meeting_datetime'], dump_only=True)
    survey = ma.Nested(
        'app.survey_resources.surveys.schemas.SurveySchema',
        only=['row_id', 'creator', 'agenda', 'title'], dump_only=True)
    ca_open_meeting = ma.Nested(
        'app.corporate_access_resources.ca_open_meetings.schemas'
        '.CAOpenMeetingSchema', only=[
            'row_id', 'creator', 'title', 'event_type_id',
            'event_sub_type_id', 'started_at', 'ended_at'], dump_only=True)
    ca_open_meeting_inquiry = ma.Nested(
        'app.corporate_access_resources.ca_open_meeting_inquiries.schemas'
        '.CAOpenMeetingInquirySchema',
        only=['creator', 'ca_open_meeting_slot', 'row_id'], dump_only=True)
    ca_open_meeting_slot = ma.Nested(
        'app.corporate_access_resources.ca_open_meeting_slots.schemas'
        '.CAOpenMeetingSlotSchema',
        only=['row_id'], dump_only=True)
    admin_publish_notification = ma.Nested(
        'app.resources.admin_publish_notifications.schemas.'
        'AdminPublishNotificationSchema', only=[
            'row_id', 'title', 'description'], dump_only=True)
    project = ma.Nested(
        'app.toolkit_resources.projects.schemas.'
        'ProjectSchema', only=[
            'row_id', 'project_name', 'creator'], dump_only=True)

    activity = ma.Nested(
        'app.activity.activities.schemas.ActivitySchema', only=[
        'row_id','agenda','created_date','started_at','ended_at','creator'],
        dump_only=True)

    bse_corp_feed = ma.Nested(
        'app.resources.bse.schemas.BseCorpSchema', only=['row_id'],
        dump_only=True
    )

    corporate_announcement = ma.Nested(
        'app.resources.corporate_announcements.schemas.CorporateAnnouncementSchema',
        only=['row_id'], dump_only=True
    )

class NotificationReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "notification" filters from request args
    """
    notification_group = fields.String(load_only=True, validate=validate.OneOf(
        NOTIFY.NOTIFICATION_GROUPS))
    notification_type = fields.String(load_only=True, validate=validate.OneOf(
        NOTIFY.NOTIFICATION_TYPES))

    main_filter = fields.String(load_only=True, validate=validate.OneOf(
        NOTIFY.TYPE_LISTS))