import datetime
import mimetypes
import csv

from flask_script import Command, Option
from sqlalchemy import func, or_

from app import db
from app.resources.countries.schemas import CountrySchema
from app.resources.states.schemas import StateSchema
from app.resources.cities.schemas import CitySchema
from app.resources.states.models import State
from app.resources.countries.models import Country
from app.resources.cities.models import City


country_schema = CountrySchema()
state_schema = StateSchema()
city_schema = CitySchema()


class ImportStatesCities(Command):
    """
    Command to import states and cities from csv files

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
        Option('--user_id', '-user', dest='user_id', required=True),
        Option('--csv_file', '-csv', dest='csv_file', required=True),
        Option('--file', '-file', dest='file', required=True),

    ]

    def run(self, verbose, dry, user_id, csv_file, file):
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('Adding states and cities')

        try:
            count = 0
            batch_size = 100

            if csv_file:
                # check file is csv
                file_type = mimetypes.guess_type(csv_file)[0]
                if file_type and '/' in file_type:
                    file_type = file_type.split('/')[1]
                if file_type != 'csv':
                    print('File type not allowed')

                with open(csv_file, 'r', newline='',
                          encoding='utf-8') as f:
                    if file == 'country':
                        next(f)
                    for row in csv.reader(f, delimiter='\t'):
                        # read a line (row) at a time
                        if not row[0].strip():
                            # blank, so skip
                            continue
                        # replace non-breaking spaces
                        row = [c.replace(u'\xa0', ' ') for c in row]
                        if not row[0].strip():
                            # blank, so skip
                            continue
                        row = [c.strip() for c in row]
                        # load data to schema
                        if file == 'country':
                            data, errors = country_schema.load({
                                'country_name': row[4],
                                'country_code': row[0]
                            })
                            if errors:
                                continue
                            dup_country = Country.query.filter(
                                or_(func.lower(Country.country_name) ==
                                    data.country_name.lower(),
                                    Country.country_name == data.country_name),
                                Country.country_code ==
                                data.country_code).first()
                            if dup_country:
                                continue
                            data.created_by = user_id
                            data.updated_by = user_id
                            db.session.add(data)
                            count = count + 1
                            if count >= batch_size:
                                db.session.commit()
                                count = 0
                        elif file == 'state':
                            country = Country.query.filter(
                                Country.country_code == row[0].split(
                                    '.')[0]).first()
                            if country:
                                data, errors = state_schema.load({
                                    'state_name': row[2],
                                    'state_code': row[0].replace(".", ""),
                                    'country_id': country.row_id
                                })
                                if errors:
                                    continue
                                dup_state = State.query.filter(
                                    State.state_code == data.state_code,
                                    State.country_id ==
                                    data.country_id).first()
                                if dup_state:
                                    continue
                                data.created_by = user_id
                                data.updated_by = user_id
                                db.session.add(data)
                                count = count + 1
                                if count >= batch_size:
                                    db.session.commit()
                                    count = 0
                        elif file == 'city':
                            state = State.query.filter(
                                State.state_code == row[8] + row[10]
                            ).first()
                            if state:
                                data, errors = CitySchema().load({
                                    'city_name': row[1],
                                    'state_id': state.row_id,
                                    'country_id': state.country_id
                                })
                                if errors:
                                    continue
                                dup_city = City.query.filter(
                                    or_(func.lower(City.city_name) ==
                                        data.city_name.lower(),
                                        City.city_name == data.city_name),
                                    City.state_id == data.state_id,
                                    City.country_id == data.country_id).first()
                                if dup_city:
                                    continue
                                data.created_by = user_id
                                data.updated_by = user_id
                                db.session.add(data)
                                count = count + 1
                                if count >= batch_size:
                                    db.session.commit()
                                    count = 0
                            else:
                                print(row)

            if count:
                db.session.commit()

        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
