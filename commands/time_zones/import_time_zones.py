import json
import datetime
import mimetypes

from flask_script import Command, Option

from app import db
from app.resources.ref_time_zones.schemas import RefTimeZoneSchema


class ImportTimeZones(Command):
    """
    Command to import time zone from an json file

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
        Option('--json_file', '-json', dest='json_file', required=True),
    ]

    def run(self, verbose, dry, json_file):
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('Adding time zones')

        try:
            if json_file:
                # check file is json
                file_type = mimetypes.guess_type(json_file)[0]
                if file_type and '/' in file_type:
                    file_type = file_type.split('/')[1]
                if file_type != 'json':
                    print('File type not allowed')

                with open(json_file) as jsf:
                    json_all_data = json.load(jsf)
                    for json_data in json_all_data:
                        if 'text' in json_data:
                            json_data['display_value'] = json_data.pop('text')
                        if 'offset' in json_data:
                            json_data['offset'] = str(json_data.pop('offset'))

                        data, errors = RefTimeZoneSchema().load(json_data)
                        if errors:
                            continue
                        db.session.add(data)
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
