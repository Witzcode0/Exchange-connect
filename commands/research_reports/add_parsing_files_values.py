import datetime

from flask_script import Command, Option
from flask import current_app
from sqlalchemy import and_, or_

from app import db
from app.resources.users.models import User
from app.resources.contact_requests.models import ContactRequest
from app.resources.contacts.models import Contact
from app.semidocument_resources.parsing_files.models import ParsingFile


class AddParsingFiles(Command):
    """
    Command to add default contacts to existing users
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
            print('Adding parsing files ...')
        try:
            companies_list = [{'Bharti_Airtel_Ltd': 447}, {'Hero_MotoCorp': 309}, {'Hindustan_Unilever': 147},
                              {'Bajaj_Auto': 254}, {'Asian_Paints': 297},
                              {'Adani_Ports': 564}, {'Britannia_Industries': 261}, {'Power_Grid': 447},
                              {'Maruti_Suzuki': 185}, {'NTPC_Ltd': 586}]

            # live_account_id = [193, 520, 540, 147, 123, 35, 221, 1012, 801, 918]
            staging_account_id = [258, 585, 605, 212, 188, 100, 286, 1078, 866, 984]
            # test_account_id = [30, 31, 32]
            parsed_files = []
            batch_size = 500
            counter = 0

            for dict in companies_list:
                account_id = staging_account_id[counter]
                for key, val in dict.items():
                    for i in range(1, val + 1):
                        file_name = key+"{i:03d}".format(i=i)+".png"
                        data = ParsingFile(
                            filename=file_name,
                            account_id=account_id)
                        parsed_files.append(data)
                        if len(parsed_files) >= batch_size:
                            db.session.add_all(parsed_files)
                            db.session.commit()
                            parsed_files = []
                    info = ParsingFile(
                        filename=key+'.txt',
                        account_id=account_id)
                    db.session.add(info)
                    info = ParsingFile(
                        filename=key + '_class_index.csv',
                        account_id=account_id)
                    db.session.add(info)
                    info = ParsingFile(
                        filename=key + '_page_wise_stats.csv',
                        account_id=account_id)
                    db.session.add(info)
                    info = ParsingFile(
                        filename=key + '_text_index.csv',
                        account_id=account_id)
                    db.session.add(info)
                    db.session.commit()

                counter += 1

            if parsed_files:
                db.session.add_all(parsed_files)
                db.session.commit()

        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
