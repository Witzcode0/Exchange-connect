import datetime

from flask_script import Command, Option
from sqlalchemy.orm import load_only
from sqlalchemy import func, case

from app import db
from app.resources.events.models import Event
from app.resources.event_invites.models import EventInvite
from app.resources.event_invites.helpers import calculate_avg_rating
from app.resources.event_invites import constants as EVENT_INVITE


class UpdateCountsInEvents(Command):
    """
    Command to update existing events with invite numbers

    :arg verbose:        print progress
    :arg dry:
        dry run
    """
    option_list = [
        Option('--verbose', '-v', dest='verbose', action='store_true',
               default=False),
        Option('--dry', '-dry', dest='dry', action='store_true',
               default=False),
    ]

    def run(self, verbose, dry):
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('Updating counts in events ...')
        try:
            event = db.session.query(
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
                EventInvite.event_id).all()
            for e in event:
                Event.query.filter(Event.row_id == e.event_id).update(
                    {Event.participated: e[1],
                     Event.not_participated: e[2],
                     Event.maybe_participated: e[3],
                     Event.attended_participated: e[4]},
                    synchronize_session=False)
                db.session.commit()

            event_data = Event.query.options(load_only('row_id')).all()
            event_ids = [ev.row_id for ev in event_data]
            for event_id in event_ids:
                Event.query.filter(Event.row_id == event_id).update(
                    {Event.avg_rating: calculate_avg_rating(event_id)},
                    synchronize_session=False)
                db.session.commit()

        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
