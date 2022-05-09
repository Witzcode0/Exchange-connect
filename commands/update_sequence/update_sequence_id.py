import json
import datetime
import mimetypes

from flask_script import Command, Option
from sqlalchemy.orm import load_only

from app import db
from app.corporate_access_resources.corporate_access_events.models import \
    CorporateAccessEvent
from app.corporate_access_resources.corporate_access_event_participants.\
    models import CorporateAccessEventParticipant
from app.corporate_access_resources.corporate_access_event_rsvps.models \
    import CorporateAccessEventRSVP
from app.webinar_resources.webinars.models import Webinar
from app.webinar_resources.webinar_participants.models import WebinarParticipant
from app.webinar_resources.webinar_rsvps.models import WebinarRSVP
from app.webcast_resources.webcasts.models import Webcast
from app.webcast_resources.webcast_participants.models import WebcastParticipant
from app.webcast_resources.webcast_rsvps.models import WebcastRSVP


class UpdateSequenceId(Command):
    """
    Command to update sequence id for old participant and rsvp of CAEvent,
    webinar and webcast according row_id of participant and rsvp

    :arg verbose:
        print progress
    :arg dry:
        dry run
    """

    option_list = [
        Option('--verbose', '-v', dest='verbose', action='store_true',
               default=False),
        Option('--dry', '-dry', dest='dry', action='store_true',
               default=False),
        Option('--event_type', '-event_type', dest='event_type', required=True),
    ]

    def run(self, verbose, dry, event_type):
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('Updating sequence id')

        try:
            if event_type == 'caevent':
                caevent_ids = [cae.row_id for cae in
                               CorporateAccessEvent.query.options(
                                   load_only('row_id')).all()]
                for row_id in caevent_ids:
                    caevent_participants = None
                    cae_rsvps = None
                    caevent_participants = \
                        CorporateAccessEventParticipant.query.filter(
                            CorporateAccessEventParticipant.
                            corporate_access_event_id == row_id
                        ).options(load_only('row_id', 'sequence_id')).all()
                    if caevent_participants:
                        sequence_count = 1
                        for cae_pcpt in sorted(
                                caevent_participants, key=lambda x:(x.row_id)):
                            if not cae_pcpt.sequence_id:
                                cae_pcpt.sequence_id = sequence_count
                                db.session.add(cae_pcpt)
                                sequence_count += 1
                            else:
                                sequence_count += 1

                    cae_rsvps = CorporateAccessEventRSVP.query.filter(
                        CorporateAccessEventRSVP.corporate_access_event_id ==
                        row_id).options(load_only('row_id', 'sequence_id')).all()
                    if cae_rsvps:
                        rsvp_sequence_count = 1
                        for cae_rsvp in sorted(
                                cae_rsvps, key=lambda x: (x.row_id)):
                            if not cae_rsvp.sequence_id:
                                cae_rsvp.sequence_id = rsvp_sequence_count
                                db.session.add(cae_rsvp)
                                rsvp_sequence_count += 1
                            else:
                                rsvp_sequence_count += 1
                    db.session.commit()

            if event_type == 'webinar':
                webinar_ids = [web.row_id for web in Webinar.query.options(
                                   load_only('row_id')).all()]
                for row_id in webinar_ids:
                    webinar_participants = None
                    webinar_rsvps = None
                    webinar_participants = \
                        WebinarParticipant.query.filter(
                            WebinarParticipant.webinar_id == row_id
                        ).options(load_only('row_id', 'sequence_id')).all()
                    if webinar_participants:
                        sequence_count = 1
                        for webinar_pcpt in sorted(
                                webinar_participants, key=lambda x:(x.row_id)):
                            if not webinar_pcpt.sequence_id:
                                webinar_pcpt.sequence_id = sequence_count
                                db.session.add(webinar_pcpt)
                                sequence_count += 1
                            else:
                                sequence_count += 1

                    webinar_rsvps = WebinarRSVP.query.filter(
                        WebinarRSVP.webinar_id == row_id).options(
                        load_only('row_id', 'sequence_id')).all()
                    if webinar_rsvps:
                        rsvp_sequence_count = 1
                        for webinar_rsvp in sorted(
                                webinar_rsvps, key=lambda x: (x.row_id)):
                            if not webinar_rsvp.sequence_id:
                                webinar_rsvp.sequence_id = rsvp_sequence_count
                                db.session.add(webinar_rsvp)
                                rsvp_sequence_count += 1
                            else:
                                rsvp_sequence_count += 1
                    db.session.commit()

            if event_type == 'webcast':
                webcast_ids = [web.row_id for web in Webcast.query.options(
                                   load_only('row_id')).all()]
                for row_id in webcast_ids:
                    webcast_participants = None
                    webcast_rsvps = None
                    webcast_participants = \
                        WebcastParticipant.query.filter(
                            WebcastParticipant.webcast_id == row_id
                        ).options(load_only('row_id', 'sequence_id')).all()
                    if webcast_participants:
                        sequence_count = 1
                        for webcast_pcpt in sorted(
                                webcast_participants, key=lambda x:(x.row_id)):
                            if not webcast_pcpt.sequence_id:
                                webcast_pcpt.sequence_id = sequence_count
                                db.session.add(webcast_pcpt)
                                sequence_count += 1
                            else:
                                sequence_count += 1

                    webcast_rsvps = WebcastRSVP.query.filter(
                        WebcastRSVP.webcast_id == row_id).options(
                        load_only('row_id', 'sequence_id')).all()
                    if webcast_rsvps:
                        rsvp_sequence_count = 1
                        for webcast_rsvp in sorted(
                                webcast_rsvps, key=lambda x: (x.row_id)):
                            if not webcast_rsvp.sequence_id:
                                webcast_rsvp.sequence_id = rsvp_sequence_count
                                db.session.add(webcast_rsvp)
                                rsvp_sequence_count += 1
                            else:
                                rsvp_sequence_count += 1
                    db.session.commit()

        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
