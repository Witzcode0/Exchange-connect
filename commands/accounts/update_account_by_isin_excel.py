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
from app.resources.management_profiles.models import ManagementProfile
from app.resources.companies.models import Company
from app.base.constants import FILE_TYPES


class UpdateAccountByISINExcel(Command):
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
                    exit(0)
                invalid_list = [
                    '#n/a', '#n.a', 'n.a', 'n/a', '#calc', '#N/A', 'NULL',
                    '--', '42', 42]

                def _get_clean_data(val, default=None):
                    if str(val) in invalid_list:
                        return default
                    return str(val)
                total = 0

                company_wb = open_workbook(xls_file)
                if company_wb:
                    sheet = company_wb.sheets()[0]
                    number_of_rows = sheet.nrows
                    missing_isin_sedol = []
                    updated_accounts = []
                    created_accounts = []
                    not_created = []
                    not_updated = []
                    for row in range(1, number_of_rows):
                        is_update = False
                        if verbose:
                            print(str(row) + '/' + str(number_of_rows))
                        country = sheet.cell(row, 8).value #10
                        if country not in ['Hong Kong', 'China']:
                            continue
                        isin = sheet.cell(row, 1).value #3
                        if isin in invalid_list:
                            missing_isin_sedol.append(row)
                            continue
                        try:
                            sedol = str(int(sheet.cell(row, 2).value)) #4
                        except ValueError:
                            sedol = str(sheet.cell(row, 2).value) # 4

                        if sedol in invalid_list:
                            missing_isin_sedol.append(row)
                            continue
                        total += 1
                        name = sheet.cell(row, 4).value #6
                        # ec_identifier = sheet.cell(row, 1).value
                        identifier = _get_clean_data(sheet.cell(row, 0).value) #2
                        perm_security_id = _get_clean_data(sheet.cell(row, 3).value) #5
                        fsym_id = _get_clean_data(sheet.cell(row, 30).value) #32
                        nse_symbol = _get_clean_data(sheet.cell(row, 31).value) #33
                        website = _get_clean_data(sheet.cell(row, 13).value)

                        region = _get_clean_data(sheet.cell(row, 7).value)
                        country = _get_clean_data(sheet.cell(row, 8).value)
                        state = _get_clean_data(sheet.cell(row, 9).value)
                        city = _get_clean_data(sheet.cell(row, 10).value)
                        address = _get_clean_data(sheet.cell(row, 11).value)
                        description = _get_clean_data(sheet.cell(row, 12).value)
                        phone_number = _get_clean_data(
                            sheet.cell(row, 14).value, '')

                        account = Account.query.filter(
                            Account.isin_number == isin,
                            Account.sedol == sedol).first()
                        if not account:
                            account = Account.query.filter(
                                func.lower(Account.account_name) == name.lower()
                            ).first()

                        account_detail = {
                            'account_type': account_type,
                            'account_name': name,
                            # 'ec_identifier': ec_identifier,
                            'identifier': identifier,
                            'isin_number': isin,
                            'sedol': sedol,
                            'perm_security_id': perm_security_id,
                            'fsym_id': fsym_id,
                            'website': website,
                            'profile': {
                                'region': region,
                                'country': country,
                                'address_city': city,
                                'address_state': state,
                                'address_country': country,
                                'address_street_one': address,
                                'description': description,
                                'phone_primary': phone_number.replace('.', '')
                                }
                        }

                        if account:
                            is_update = True
                            # update record
                            account.updated_by = user_id
                            if identifier:
                                account.identifier = identifier
                            account.perm_security_id = perm_security_id
                            account.nse_symbol = nse_symbol
                            account.fsym_id = fsym_id
                            account.website = website
                            # account.ec_identifier = ec_identifier
                        else:
                            # add new account
                            account, errors = AccountSchema().load(
                                account_detail)
                            if errors:
                                not_updated.append(isin)
                                print(errors)
                                continue
                            # no errors, add to db
                            account.created_by = user_id
                            account.updated_by = user_id
                            account.profile.account_type = account_type
                            account.stats = AccountStats()
                            account.settings = AccountSettings()
                        try:
                            db.session.add(account)
                            db.session.commit()
                            mngt_cnt = len(account.profile.management_profiles)
                            managements = []
                            start = 15
                            for i in range(5):
                                name = str(sheet.cell(row, start).value)
                                designation = str(
                                    sheet.cell(row, start + 1).value)
                                email = str(sheet.cell(row, start + 2).value)
                                start += 3
                                mngt_cnt += 1
                                if name and name not in invalid_list:
                                    if designation in invalid_list:
                                        designation = ''
                                    if email in invalid_list:
                                        email = ''
                                    managements.append(
                                        ManagementProfile(
                                            **{'name': name, 'sequence_id': mngt_cnt,
                                            'designation': designation,
                                            'email': email,
                                            'account_profile_id': account.profile.row_id}))

                                else:
                                    break
                            if is_update:
                                updated_accounts.append((isin, sedol))
                            else:
                                created_accounts.append((isin, sedol))
                                db.session.add_all(managements)
                                db.session.commit()
                        except IntegrityError as e:
                            db.session.rollback()
                            if (APP.DB_ALREADY_EXISTS in
                                    e.orig.diag.message_detail.lower()):
                                print(str(row) + '/' + str(
                                    number_of_rows))
                                print(sheet.row_values(row))
                            if 'is_update' in locals():
                                if is_update:
                                    not_updated.append((isin, sedol))
                                else:
                                    not_created.append((isin, sedol))
                            continue
            print('created {}'.format(len(created_accounts)))
            print('updated {}'.format(len(updated_accounts)))
            print('total {}'.format(total))
            print('not created')
            print(not_created)
            print('not updated')
            print(not_updated)
            print('{} rows with missing isin'.format(len(missing_isin_sedol)))
            print(missing_isin_sedol)

        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
