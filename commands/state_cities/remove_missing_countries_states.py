import datetime

from flask_script import Command, Option

from app import db
from app.resources.states.models import State
from app.resources.countries.models import Country
from app.resources.cities.models import City


class RemoveCountriesStates(Command):
    """
    Command to removed countries and states from db

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
            print('Deleting countries and states')

        try:
            states = State.query.all()
            countries = Country.query.all()
            for state in states:
                cities = City.query.filter(
                    City.state_id == state.row_id).all()
                if not cities:
                    # Removed state not present in city table
                    db.session.delete(state)
                    db.session.commit()
            for country in countries:
                get_state = State.query.filter(
                    State.country_id == country.row_id).all()
                if not get_state:
                    # Removed country not present in state table
                    db.session.delete(country)
                    db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
