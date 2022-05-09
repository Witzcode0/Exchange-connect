import datetime

from flask_script import Command, Option
from sqlalchemy.orm import load_only
from sqlalchemy import func, case

from app.corporate_access_resources.corporate_access_events.models import \
    caeventparticipantcompanies, CorporateAccessEvent

from app import db


class UpdateCAEventAccountID(Command):
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
            print('Updating account id of in caevents ...')
        try:
            ca_event_data = CorporateAccessEvent.query.filter(
                CorporateAccessEvent.created_by == 1).all()
            for caevent in ca_event_data:
                for comp in caevent.caevent_participant_companies:
                    # print(comp)
                    print(comp.row_id, comp.account_name)
                    caevent.account_id = comp.row_id
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')