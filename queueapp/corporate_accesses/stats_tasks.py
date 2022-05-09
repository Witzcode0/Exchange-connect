"""
corporate access event stats related task
"""

from app import db
# from sqlalchemy.orm import load_only

from queueapp.tasks import celery_app, logger

from app.corporate_access_resources.corporate_access_event_collaborators. \
    models import CorporateAccessEventCollaborator
from app.corporate_access_resources.corporate_access_event_attendees.\
    models import CorporateAccessEventAttendee
from app.corporate_access_resources.corporate_access_event_hosts.\
    models import CorporateAccessEventHost
from app.corporate_access_resources.corporate_access_event_inquiries.\
    models import CorporateAccessEventInquiry
from app.corporate_access_resources.corporate_access_event_invitees.\
    models import CorporateAccessEventInvitee
from app.corporate_access_resources.corporate_access_event_participants.\
    models import CorporateAccessEventParticipant
from app.corporate_access_resources.corporate_access_event_slots.\
    models import CorporateAccessEventSlot
from app.corporate_access_resources.corporate_access_event_rsvps.\
    models import CorporateAccessEventRSVP
from app.corporate_access_resources.corporate_access_event_stats.\
    models import CorporateAccessEventStats
from app.corporate_access_resources.corporate_access_events.models import \
    CorporateAccessEvent
from app.corporate_access_resources.corporate_access_event_agendas.models \
    import CorporateAccessEventAgenda


@celery_app.task(bind=True, ignore_result=True)
def update_corporate_event_stats(self, result, row_id, *args, **kwargs):
    """

    """
    if result:
        try:
            event_data = CorporateAccessEvent.query.get(row_id)
            participants = CorporateAccessEventParticipant.query.filter_by(
                corporate_access_event_id=row_id).all()
            hosts = CorporateAccessEventHost.query.filter_by(
                corporate_access_event_id=row_id).all()
            rsvps = CorporateAccessEventRSVP.query.filter_by(
                corporate_access_event_id=row_id).all()
            collaboartor = CorporateAccessEventCollaborator.query.filter_by(
                corporate_access_event_id=row_id).all()
            slots = CorporateAccessEventSlot.query.filter_by(
                event_id=row_id).all()

            invitees = CorporateAccessEventInvitee.query.filter_by(
                corporate_access_event_id=row_id).all()
            inquires = CorporateAccessEventInquiry.query.filter_by(
                corporate_access_event_id=row_id).all()
            attendees = CorporateAccessEventAttendee.query.filter_by(
                corporate_access_event_id=row_id).all()
            agendas = CorporateAccessEventAgenda.query.filter_by(
                corporate_access_event_id=row_id).all()
            stats_data = CorporateAccessEventStats.query.filter_by(
                corporate_access_event_id=row_id).first()

            participants_count = 0
            hosts_count = 0
            rsvps_count = 0
            collaborators_count = 0
            slots_count = 0
            seats_count = 0
            booked_count = 0
            invitees_count = 0
            inquiries_count = 0
            attended_count = 0
            attendee_rating = 0
            attendee_given_rating_count = 0
            files_count = 0
            avg_attendee_rating = 0
            total_joined = 0
            total_agendas = 0
            total_non_slot_meetings = 0

            if event_data:
                if event_data.files:
                    files_count = len(event_data.files)
                if event_data.joined_invitees:
                    total_joined = len(event_data.joined_invitees)
                if not event_data.event_sub_type.has_slots:
                    total_non_slot_meetings = 1
            if agendas:
                total_agendas = len(agendas)
            if participants:
                participants_count = len(participants)
            if hosts:
                hosts_count = len(hosts)
            if rsvps:
                rsvps_count = len(rsvps)
            if collaboartor:
                collaborators_count = len(collaboartor)
            if slots:
                for slot in slots:
                    slots_count = slots_count + 1
                    seats_count = seats_count + slot.bookable_seats
                    booked_count = booked_count + slot.booked_seats

            if invitees:
                invitees_count = len(invitees)
            if inquires:
                inquiries_count = len(inquires)
            if attendees:
                for attendee in attendees:
                    attended_count = attended_count + 1
                    if attendee.rating is not None:
                        attendee_given_rating_count =\
                            attendee_given_rating_count + 1
                        attendee_rating = attendee_rating + attendee.rating
            if attendee_given_rating_count != 0:
                avg_attendee_rating =\
                    attendee_rating / attendee_given_rating_count

            if stats_data:
                stats_data.total_participants = participants_count
                stats_data.total_hosts = hosts_count
                stats_data.total_rsvps = rsvps_count
                stats_data.total_collaborators = collaborators_count
                stats_data.total_slots = slots_count
                stats_data.total_seats = seats_count
                stats_data.total_booked = booked_count
                stats_data.total_invitees = invitees_count
                stats_data.total_inquiries = inquiries_count
                stats_data.total_attended = attended_count
                stats_data.total_files = files_count
                stats_data.average_rating = avg_attendee_rating
                stats_data.total_joined = total_joined
                stats_data.total_agendas = total_agendas
                stats_data.total_non_slot_meetings = total_non_slot_meetings
                db.session.add(stats_data)
            db.session.commit()

            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False
    return result
