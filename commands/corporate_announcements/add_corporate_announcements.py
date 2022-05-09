import datetime

from flask_script import Command, Option
from sqlalchemy import and_, or_

from app import db
from app.corporate_access_resources.ref_event_sub_types.models import \
    CARefEventSubType
from app.corporate_access_resources.corporate_access_events.models import \
    CorporateAccessEvent
from app.resources.corporate_announcements.models import CorporateAnnouncement
from app.resources.corporate_announcements import constants as CORPO


class AddCorporateAnnouncement(Command):
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
            print('Adding Corporate announcements ...')
        try:
            event_sub_types = CARefEventSubType.query.filter(
                CARefEventSubType.show_time.is_(True)).all()
            for sub_type in event_sub_types:
                ca_events = CorporateAccessEvent.query.filter(and_(
                    CorporateAccessEvent.created_by == 1,
                    CorporateAccessEvent.event_sub_type_id == sub_type.row_id,
                    or_(
                        CorporateAccessEvent.audio_filename.isnot(None),
                        CorporateAccessEvent.transcript_filename.isnot(None)
                    ))).all()
                for event in ca_events:
                    print(event.row_id)
                    if event.audio_filename:
                        if not CorporateAnnouncement.query.filter(
                                CorporateAnnouncement.ca_event_audio_file_id ==
                                event.row_id).first():
                            db.session.add(CorporateAnnouncement(
                                announcement_date=event.started_at,
                                category=CORPO.CANNC_CONCAL_TRANSCRIPTS,
                                subject=event.title,
                                description=event.description,
                                ca_event_audio_file_id=event.row_id,
                                account_id=event.account_id,
                                created_by=event.created_by,
                                updated_by=event.updated_by))
                    if event.transcript_filename:
                        if not CorporateAnnouncement.query.filter(
                                CorporateAnnouncement.
                                ca_event_transcript_file_id == event.row_id
                                ).first():
                            db.session.add(CorporateAnnouncement(
                                announcement_date=event.started_at,
                                category=CORPO.CANNC_CONCAL_TRANSCRIPTS,
                                subject=event.title,
                                description=event.description,
                                ca_event_transcript_file_id=event.row_id,
                                account_id=event.account_id,
                                created_by=event.created_by,
                                updated_by=event.updated_by))
                    db.session.commit()

        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
