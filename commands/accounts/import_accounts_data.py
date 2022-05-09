import datetime
import mimetypes

from xlrd import open_workbook
from flask_script import Command, Option
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app import db
from app.base import constants as APP
from app.resources.accounts.models import Account
from app.resources.account_stats.models import AccountStats
from app.resources.account_settings.models import AccountSettings
from app.resources.accounts.schemas import AccountSchema
from app.resources.companies.models import Company
from app.base.constants import FILE_TYPES


class ImportAccountData(Command):
    """
    Command to import account data from xlsx file

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
        Option('--account_type', '-account_type', dest='account_type',
               required=True),
        Option('--xls_file', '-xls', dest='xls_file', required=True),
    ]

    def run(self, verbose, dry, user_id, account_type, xls_file):
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('Adding and updating existing accounts')

        try:
            if xls_file:
                # check file is xls
                file_type = mimetypes.guess_type(xls_file)[0]

                if file_type and '/' in file_type:
                    file_type = file_type.split('/')[1]
                if file_type not in FILE_TYPES:
                    print('File type not allowed')

                # List to check if any invalid entries.
                invalid_list = [
                    '#n/a', '#n.a', 'n.a', 'n/a', '#calc', '42', 42]
                company_wb = open_workbook(xls_file)
                if company_wb:
                    sheet = company_wb.sheets()[1]
                    number_of_rows = sheet.nrows
                    for row in range(1, number_of_rows):
                        if verbose:
                            print(str(row) + '/' + str(number_of_rows))
                        if str(sheet.cell(row, 2).value).lower() in \
                                invalid_list:
                            print('ISIN Number is invalid for row', row)
                            print(sheet.row_values(row))
                            continue
                        market_cap = sheet.cell(row, 6).value
                        # market cap in invalid list, take it as None/Null.
                        if market_cap in invalid_list:
                            market_cap = None
                            print('Market cap is invalid for row', row)
                            print(sheet.row_values(row))
                        company = Company.query.filter(
                            Company.isin_number == str(
                                sheet.cell(row, 2).value)).first()
                        if company:
                            account = Account.query.filter(
                                func.lower(Account.account_name) ==
                                company.company_name.lower()).first()

                            if (not company.sector_id or
                                    not company.industry_id):
                                print('Possible missing sector/industry data '
                                      'in company = ', str(company.row_id))
                                continue
                            sector_row_id = company.sector_id
                            industry_row_id = company.industry_id

                            account_detail = {
                                'account_type': account_type,
                                'account_name': company.company_name,
                                'identifier': company.identifier,
                                'isin_number': company.isin_number,
                                'sedol': company.sedol,
                                'profile': {
                                    'sector_id': sector_row_id,
                                    'industry_id': industry_row_id,
                                    'region': company.region,
                                    'country': company.country,
                                    'address_city': company.city,
                                    'address_state': company.state,
                                    'address_country': company.country,
                                    'address_street_one': company.address,
                                    'description': company.business_desc,
                                    'phone_primary':
                                    company.telephone_number
                                }
                            }
                            if account:
                                # account has activation_date, skip it
                                if account.activation_date:
                                    continue

                                # account has no activation_date,
                                # update record
                                account.updated_by = user_id
                                account.account_name = company.company_name
                                account.identifier = company.identifier
                                account.sedol = company.sedol
                                account.profile.account_id = account.row_id
                                account.profile.account_type = account_type
                                account.profile.sector_id = sector_row_id
                                account.profile.industry_id = \
                                    industry_row_id
                                account.profile.region = company.region
                                account.profile.country = company.country
                                account.profile.address_city = company.city
                                account.profile.address_state = \
                                    company.state
                                account.profile.address_country = \
                                    company.country
                                account.profile.address_street_one = \
                                    company.address
                                account.profile.description = \
                                    company.business_desc
                                account.profile.phone_primary = \
                                    company.telephone_number
                                account.profile.market_cap = market_cap
                                # assigning existing account to 'data'
                                data = account
                            else:
                                # add new account
                                data, errors = AccountSchema().load(
                                    account_detail)
                                if errors:
                                    continue
                                # no errors, add to db
                                data.created_by = user_id
                                data.updated_by = user_id
                                data.profile.account_type = account_type
                                data.profile.market_cap = market_cap
                                data.stats = AccountStats()
                                data.settings = AccountSettings()
                        try:
                            db.session.add(data)
                            db.session.commit()
                        except IntegrityError as e:
                            db.session.rollback()
                            if (APP.DB_ALREADY_EXISTS in
                                    e.orig.diag.message_detail.lower()):
                                print(str(row) + '/' + str(
                                    number_of_rows))
                                print(sheet.row_values(row))
                            continue

        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
