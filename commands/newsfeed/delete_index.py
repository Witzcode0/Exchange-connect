import datetime

from flask_script import Command, Option
from flask import current_app
from flask_restful import abort

from app.base import constants as APP
from app import es

class DeleteIndex(Command):
    """
    Command to delete index(daily-news) of elasticsearch

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
            print('Updating news ...')

        try:
            index = APP.NW_ES_INDEX
            es.indices.delete(index = index, ignore=[400, 404])

        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')