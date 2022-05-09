"""
Webcast_stats related task
"""

from app import db

from queueapp.tasks import celery_app, logger

from app.webcast_resources.webcast_attendees.models import (
    WebcastAttendee)
from app.webcast_resources.webcast_hosts.models import (
    WebcastHost)
from app.webcast_resources.webcast_invitees.models import (
    WebcastInvitee)
from app.webcast_resources.webcast_participants.models import (
    WebcastParticipant)
from app.webcast_resources.webcast_rsvps.models import (
    WebcastRSVP)
from app.webcast_resources.webcast_answers.models import (
    WebcastAnswer)
from app.webcast_resources.webcast_questions.models import (
    WebcastQuestion)
from app.webcast_resources.webcast_stats.models import (
    WebcastStats)
from app.webcast_resources.webcasts.models import Webcast


@celery_app.task(bind=True, ignore_result=True)
def update_webcast_stats(self, result, row_id, *args, **kwargs):
    """
    update the webcast_stats for a webinar
    param row_id:
        webcast_id
    """
    if result:
        try:
            webcast_data = Webcast.query.get(row_id)
            attendees = WebcastAttendee.query.filter_by(
                webcast_id=row_id).all()
            hosts = WebcastHost.query.filter_by(webcast_id=row_id).all()
            invitees = WebcastInvitee.query.filter_by(webcast_id=row_id).all()
            participants = WebcastParticipant.query.filter_by(
                webcast_id=row_id).all()
            rsvps = WebcastRSVP.query.filter_by(webcast_id=row_id).all()
            answers = WebcastAnswer.query.filter_by(webcast_id=row_id).all()
            questions = WebcastQuestion.query.filter_by(
                webcast_id=row_id).all()
            stats_data = WebcastStats.query.filter_by(
                webcast_id=row_id).first()

            attendee_count = 0
            host_count = 0
            invitee_count = 0
            participant_count = 0
            rsvp_count = 0
            answer_count = 0
            question_count = 0
            attendee_rating = 0
            attendee_given_rating_count = 0
            avg_attendee_rating = 0
            files_count = 0
            # get attendee count and avg_rating
            if attendees:
                for attendee in attendees:
                    attendee_count = attendee_count + 1
                    if attendee.rating is not None:
                        attendee_given_rating_count =\
                            attendee_given_rating_count + 1
                        attendee_rating = attendee_rating + attendee.rating
            if attendee_given_rating_count != 0:
                avg_attendee_rating =\
                    attendee_rating / attendee_given_rating_count
            # get hosts count
            if hosts:
                host_count = len(hosts)
            # get invitee count
            if invitees:
                invitee_count = len(invitees)
            # get participant count
            if participants:
                participant_count = len(participants)
            # get rsvps count
            if rsvps:
                rsvp_count = len(rsvps)
            # get answer count
            if answers:
                answer_count = len(answers)
            # get question count
            if questions:
                question_count = len(questions)

            if webcast_data:
                if webcast_data.files:
                    files_count = len(webcast_data.files)
            # update stats
            if stats_data:
                stats_data.total_participants = participant_count
                stats_data.total_hosts = host_count
                stats_data.total_rsvps = rsvp_count
                stats_data.total_invitees = invitee_count
                stats_data.total_attendees = attendee_count
                stats_data.total_questions = question_count
                stats_data.total_answers = answer_count
                stats_data.total_files = files_count
                stats_data.average_rating = avg_attendee_rating
                db.session.add(stats_data)
            db.session.commit()
            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False
    return result
