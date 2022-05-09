"""
Webinar stats related tasks
"""

from app import db

from queueapp.tasks import celery_app, logger

from app.webinar_resources.webinar_answers.models import WebinarAnswer
from app.webinar_resources.webinar_attendees.models import WebinarAttendee
from app.webinar_resources.webinar_chats.models import WebinarChatMessage
from app.webinar_resources.webinar_hosts.models import WebinarHost
from app.webinar_resources.webinar_invitees.models import WebinarInvitee
from app.webinar_resources.webinar_participants.models import \
    WebinarParticipant
from app.webinar_resources.webinar_questions.models import WebinarQuestion
from app.webinar_resources.webinar_rsvps.models import WebinarRSVP
from app.webinar_resources.webinar_stats.models import WebinarStats
from app.webinar_resources.webinars.models import Webinar


@celery_app.task(bind=True, ignore_result=True)
def update_webinar_stats(self, result, row_id, *args, **kwargs):
    """
    Update webinar stats for each creation and updation of any webinar module.
    """
    if result:
        try:
            webinar_data = Webinar.query.get(row_id)
            answers = WebinarAnswer.query.filter_by(webinar_id=row_id).all()
            attendees = WebinarAttendee.query.filter_by(
                webinar_id=row_id).all()
            chats = WebinarChatMessage.query.filter_by(webinar_id=row_id).all()
            hosts = WebinarHost.query.filter_by(webinar_id=row_id).all()
            invitees = WebinarInvitee.query.filter_by(webinar_id=row_id).all()
            participants = WebinarParticipant.query.filter_by(
                webinar_id=row_id).all()
            questions = WebinarQuestion.query.filter_by(
                webinar_id=row_id).all()
            rsvps = WebinarRSVP.query.filter_by(webinar_id=row_id).all()
            stats_data = WebinarStats.query.filter_by(
                webinar_id=row_id).first()

            answer_count = 0
            attendee_count = 0
            chat_count = 0
            host_count = 0
            invitee_count = 0
            participant_count = 0
            question_count = 0
            rsvp_count = 0
            attendee_rating = 0
            attendee_given_rating_count = 0
            avg_attendee_rating = 0
            files_count = 0

            # get answers count
            if answers:
                answer_count = len(answers)
            # get attendees count and avg_rating
            if attendees:
                for attendee in attendees:
                    attendee_count = attendee_count + 1
                    if attendee.rating is not None:
                        attendee_given_rating_count = \
                            attendee_given_rating_count + 1
                        attendee_rating = attendee_rating + attendee.rating
            if attendee_given_rating_count != 0:
                avg_attendee_rating = \
                    attendee_rating / attendee_given_rating_count
            # get chats count
            if chats:
                chat_count = len(chats)
            # get hosts count
            if hosts:
                host_count = len(hosts)
            # get invitees count
            if invitees:
                invitee_count = len(invitees)
            # get participants count
            if participants:
                participant_count = len(participants)
            # get questions count
            if questions:
                question_count = len(questions)
            # get rsvps count
            if rsvps:
                rsvp_count = len(rsvps)

            if webinar_data:
                if webinar_data.files:
                    files_count = len(webinar_data.files)
            # update stats
            if stats_data:
                stats_data.total_answers = answer_count
                stats_data.total_attendees = attendee_count
                stats_data.total_chat_messages = chat_count
                stats_data.total_hosts = host_count
                stats_data.total_invitees = invitee_count
                stats_data.total_participants = participant_count
                stats_data.total_rsvps = rsvp_count
                stats_data.total_questions = question_count
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
