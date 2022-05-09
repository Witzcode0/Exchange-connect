import datetime
import time
import csv
import json

from flask_script import Command, Option
from sqlalchemy import and_
from sqlalchemy.orm import load_only

from app import db
from app.resources.accounts.models import Account
from app.resources.accounts import constants as ACC


class ImportAccountKeywords(Command):

    option_list = [
        Option('--verbose', '-v', dest='verbose', action='store_true',
               default=False),
        Option('--dry', '-dry', dest='dry', action='store_true',
               default=False),
        Option('--filepath', '-f', dest='filepath', required=True)
    ]

    def run(self, verbose, dry, filepath):
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('Updating keywords from {} ...'.format(filepath))
        try:
            if not filepath.endswith('.csv'):
                print("Only csv file is allowed.")
                exit(0)
            commit_batch = 100
            commit_cnt = 0
            start_time = time.clock()
            accounts = db.session.query(Account).filter(and_(
                Account.deleted.is_(False),
                Account.account_type != ACC.ACCT_ADMIN)).options(
                load_only('row_id', 'account_name', 'keywords',
                          'identifier')).order_by(
                Account.account_name).all()
            if not accounts:
                exit(0)

            # account id vs account object for less db queries
            account_and_instance = {}
            for account in list(accounts):
                account_and_instance[account.row_id] = account
            with open(filepath) as file:
                reader = csv.reader(file)
                fields = next(reader)
                try:
                    id_index = fields.index('id')
                    keywords_index = fields.index('keys')
                    sym_index = fields.index('nse_symbol')
                except ValueError:
                    print('provide columns =  '
                          '(id, keys, nse_symbol) in header of csv')
                    exit(0)

                for row in reader:
                    try:
                        account_id = int(row[id_index])
                        account = account_and_instance[account_id]
                    except (KeyError, ValueError):
                        continue
                    keywords = row[keywords_index].split(',')
                    keywords = [word.strip() for word in keywords
                                if word.strip()]
                    keywords.append(account.identifier)
                    keywords.append(row[sym_index])
                    ac_words = account.account_name.split()
                    if len(ac_words) > 3:
                        dual = ac_words[0] + " " + ac_words[1]
                        if ac_words[1] == '&':
                            dual += " " + ac_words[2]
                        keywords.append(dual)
                    # mgmts = account.profile.management_profiles
                    # for mgmt in mgmts:
                    #     keywords.append(mgmt.name)
                    account.keywords = list(set(keywords + account.keywords))
                    db.session.add(account)
                    commit_cnt += 1
                    if commit_cnt == commit_batch:
                        db.session.commit()
                        commit_cnt = 0

            db.session.commit()
            print("finished in {} seconds".format(time.clock() - start_time))
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
