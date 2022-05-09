import datetime

from flask_script import Command, Option

from app import db
from app.resources.states.models import State
from app.resources.countries.models import Country
from app.resources.cities.models import City
from app.corporate_access_resources.corporate_access_events.models import (
    CorporateAccessEvent)
from app.corporate_access_resources.ca_open_meetings.models import (
    CAOpenMeeting)


class UpdateCityStateCountry(Command):
    """
    Command to insert city, state, country as string from respective FKs
    in CorporateAccessEvent and CAOpenMeeting

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
    ]

    def run(self, verbose, dry):
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('Updating city, countries and states')

        try:
            commit_batch = 300
            commit_cnt = 0
            for table in [CAOpenMeeting, CorporateAccessEvent]:
                query = table.query.join(
                    City, table.city_id == City.row_id, isouter=True).join(
                    State, table.state_id == State.row_id, isouter=True).join(
                    Country, table.country_id == Country.row_id, isouter=True
                ).add_columns(
                    City.city_name, State.state_name,
                    Country.country_name).all()
                for item, city, state, country in list(query):
                    item.city = city
                    item.state = state
                    item.country = country
                    db.session.add(item)
                    commit_cnt += 1
                    if commit_cnt == commit_batch:
                        db.session.commit()
                        commit_cnt = 0

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
