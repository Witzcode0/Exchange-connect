"""
Helper classes/functions for "registration request" package.
"""

from sqlalchemy.orm import load_only
from sqlalchemy import and_

from app.resources.event_invites.models import EventInvite
from app.resources.event_invites import constants as EVENT_INVITE


def calculate_avg_rating(event_id):
    """
    Calculate rating avg
    :param event_id: id of particular event
    """
    invites = None
    invites = EventInvite.query.filter(and_(
        EventInvite.event_id == event_id,
        EventInvite.status == EVENT_INVITE.ACCEPTED,
        EventInvite.deleted.is_(False))).options(
        load_only('rating')).all()
    if not invites:
        return 0.00
    ratings = [inv.rating or 0 for inv in invites]

    return round((sum(ratings) / float(len(ratings))) * 2.0) / 2.0
