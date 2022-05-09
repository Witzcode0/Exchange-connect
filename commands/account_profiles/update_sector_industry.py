import datetime
import mimetypes

from xlrd import open_workbook
from flask_script import Command, Option
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app import db
from app.base import constants as APP
from app.resources.accounts.models import Account
from app.resources.accounts.schemas import AccountSchema
from app.resources.companies.models import Company
from app.base.constants import FILE_TYPES


class UpdateSectorIndustryData(Command):
    """
    Command to update sector industry data in account profiles, from
    company table by reading company list from xlsx.

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
        Option('--xls_file', '-xls', dest='xls_file', required=True),
    ]

    def run(self, verbose, dry, xls_file):
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('Adding and updating existing accounts with sector '
                  'industry data')

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
                        company = Company.query.filter(
                            Company.isin_number == str(
                                sheet.cell(row, 2).value)).first()
                        if company:
                            account = Account.query.filter(
                                Account.isin_number ==
                                company.isin_number).first()
                            if account:
                                account.profile.sector_id = company.sector_id
                                account.profile.industry_id =\
                                    company.industry_id
                                db.session.add(account)
                    db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
