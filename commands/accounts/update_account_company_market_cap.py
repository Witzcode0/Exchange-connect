import datetime

from flask_script import Command, Option
from sqlalchemy.orm import load_only
from sqlalchemy import or_
from sqlalchemy.sql import text
from sqlalchemy import create_engine
from app import db
from app.resources.accounts.models import Account
from app.resources.account_profiles.models import AccountProfile
from config import SQLALCHEMY_EXTERNAL_DATABASE_URI
from app.domain_resources.domains.models import Domain


class UpdateAccountCompanyMarketCap(Command):
    """
    Update the market_cap in account
    """

    option_list = [
        Option('--verbose', '-v', dest='verbose', action='store_true',
               default=False),
        Option('--dry', '-dry', dest='dry', action='store_true',
               default=False),
        Option('--start_id', '-stid', dest='start_id', type=int, default=1),
        Option('--number_of_accounts', '-noa', dest='number_of_accounts',
               type=int, default=None),
        Option('--domain_id', '-did', dest='domain_id', type=int,
               default=None),
        Option('--batch', '-batch', dest='batch', type=int,
               default=100)
    ]

    def create_external_engine(self):
        # external db engine
        self.ext_db = create_engine(SQLALCHEMY_EXTERNAL_DATABASE_URI)

    def run(self, verbose, dry, start_id, number_of_accounts, domain_id, batch):

        self.create_external_engine()  # create external engine
        conn = self.ext_db.connect()  # connect to external db

        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('Updating market_cap for account and companies ...')

        try:
            domains = []
            if domain_id:
                domains = Domain.query.filter(Domain.row_id==domain_id).all()
            else:
                domains = Domain.query.all()
            optional_conditions = []
            if number_of_accounts:
                optional_conditions.append(
                    Account.row_id <= (start_id + number_of_accounts - 1))
            for domain in domains:
                # fetch all the accounts from given start_id and given batch size
                accounts = Account.query.filter(
                    Account.row_id >= start_id,
                    or_(Account.is_sme == False,
                        Account.is_sme == None),
                    Account.domain_id == domain.row_id,
                    Account.isin_number.isnot(None),
                    Account.isin_number != "",*optional_conditions).options(
                        load_only('row_id', 'isin_number')).order_by(
                    Account.row_id).all()
                start = 0
                while True:
                    account_batch = accounts[start: start+batch]
                    if not account_batch:
                        break
                    # dictionary {account_id: isin_number}
                    account_id_isin_dict = {}
                    #isin numbers stringified like "'isin1','isin2','isin3'"
                    isin_numbers = ""
                    for account in account_batch:
                        account_id_isin_dict[account.row_id] = account.isin_number
                        isin_numbers += "'" + account.isin_number + "',"
                    isin_numbers = isin_numbers[:-1]
                    # fetch all the account_profiles for updating market_cap
                    # for which isin_number is not null
                    account_profiles = AccountProfile.query.filter(
                        AccountProfile.account_id.in_(
                            account_id_isin_dict.keys())).all()

                    # fetch market_cap from external_db and append it in dictionary
                    currency = domain.currency.upper() if domain.currency else 'INR'
                    market_cap_data = conn.execute(
                        text("get_marketcap :currency, :isin"),
                        currency=currency,
                        isin=isin_numbers).fetchall()

                    isin_marketcap_dict = {}
                    for data in market_cap_data:
                        isin_marketcap_dict[data[0]] = data[1]
                    # update the market_cap in account_profiles
                    for account_profile in account_profiles:
                        isin_num = account_id_isin_dict[account_profile.account_id]
                        try:
                            marketcap = isin_marketcap_dict[isin_num]
                        except KeyError:
                            # data for given isin not sent by external server
                            continue
                        account_profile.market_cap = marketcap
                        db.session.add(account_profile)
                    db.session.commit()
                    start += batch
                print("updated {} accounts of domain {}".format(
                    len(accounts), domain.name))
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)
        finally:
            conn.close()  # always close the connection

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
