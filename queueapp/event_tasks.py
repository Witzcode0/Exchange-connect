"""
Events related tasks
"""

from sqlalchemy import func, case

from app import db
from app.resources.events.models import Event
from app.resources.event_invites.models import EventInvite
from app.resources.event_invites import constants as EVENT_INVITE
from app.resources.event_invites.helpers import calculate_avg_rating

from queueapp.tasks import celery_app, logger


@celery_app.task(bind=True, ignore_result=True)
def manage_events_counts_and_avg_rating(self, result, event_id,
                                        *args, **kwargs):
    """
    Update counts of events such as participated, not_participated,
    maybe_participated, attended_participated
    :param event_id: id of event
    """

    if result:
        try:
            event_invite = None
            event_invite = db.session.query(
                EventInvite.event_id,
                func.count(case(
                    [(EventInvite.status == EVENT_INVITE.ACCEPTED, 0)])).label(
                    'participated'),
                func.count(case(
                    [(EventInvite.status == EVENT_INVITE.REJECTED, 0)])).label(
                    'not_participated'),
                func.count(case(
                    [(EventInvite.status == EVENT_INVITE.MAYBE, 0)])).label(
                    'maybe_participated'),
                func.count(case(
                    [(EventInvite.status == EVENT_INVITE.ATTENDED, 0)])).label(
                    'attended_participated')).group_by(
                EventInvite.event_id).filter(
                EventInvite.event_id == event_id).first()

            if not event_invite:
                Event.query.filter(Event.row_id == event_id).update(
                    {Event.participated: 0,
                     Event.not_participated: 0,
                     Event.maybe_participated: 0,
                     Event.attended_participated: 0,
                     Event.avg_rating: 0.00},
                    synchronize_session=False)
            else:
                Event.query.filter(
                    Event.row_id == event_invite.event_id).update(
                    {Event.participated: event_invite[1],
                     Event.not_participated: event_invite[2],
                     Event.maybe_participated: event_invite[3],
                     Event.attended_participated: event_invite[4],
                     Event.avg_rating: calculate_avg_rating(event_id)},
                    synchronize_session=False)
            db.session.commit()

            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

        return result
