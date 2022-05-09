import datetime
from flask_script import Command, Option


class NewCompanyFeeds(Command):
    """
    Command to import bse feed to corporate announcement for newly listed companies

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
            print('tagging newly added company feeds')


        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')