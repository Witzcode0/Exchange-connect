import datetime
import mimetypes

from xlrd import open_workbook
from flask_script import Command, Option
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app import db
from app.base.constants import FILE_TYPES
from app.resources.companies.models import Company
from app.resources.sectors.models import Sector
from app.resources.industries.models import Industry
from app.resources.companies.schemas import CompanySchema


class ImportCompanyData(Command):
    """
    Command to import company data from an xlsx file

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
            print('Adding companies')

        try:
            if xls_file:
                # check file is xls
                file_type = mimetypes.guess_type(xls_file)[0]

                if file_type and '/' in file_type:
                    file_type = file_type.split('/')[1]
                if file_type not in FILE_TYPES:
                    print('File type not allowed')

                # List to check if any invalid entries.
                invalid_list = ['#n/a', '#n.a', 'n.a', 'n/a', '#calc', '42']
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
                        sector = Sector.query.filter(
                            func.lower(Sector.name) ==
                            str(sheet.cell(row, 8).value).lower(
                            )).first()
                        industry = Industry.query.filter(
                            func.lower(Industry.name) ==
                            str(sheet.cell(row, 7).value).lower(
                            )).first()
                        if company:
                            # update existing company details
                            if sector:
                                company.sector_id = sector.row_id
                            if industry:
                                company.industry_id = industry.row_id
                            company.updated_by = user_id
                            company.identifier = str(
                                sheet.cell(row, 1).value)
                            company.isin_number = str(
                                sheet.cell(row, 2).value)
                            company.sedol = str(sheet.cell(row, 3).value)
                            company.permanent_security_identifier = str(
                                sheet.cell(row, 4).value)
                            company.company_name = str(
                                sheet.cell(row, 5).value)
                            company.industry_name = str(
                                sheet.cell(row, 7).value)
                            company.sector_name = str(
                                sheet.cell(row, 8).value)
                            company.region = str(sheet.cell(row, 9).value)
                            company.country = str(
                                sheet.cell(row, 10).value)
                            company.state = str(sheet.cell(row, 11).value)
                            company.city = str(sheet.cell(row, 12).value)
                            company.address = str(
                                sheet.cell(row, 13).value)
                            company.business_desc = str(
                                sheet.cell(row, 14).value)
                            company.website = str(
                                sheet.cell(row, 15).value)
                            company.telephone_number = str(sheet.cell(
                                row, 16).value)
                            company.management_profile = [
                                {
                                    'contact_name': str(
                                        sheet.cell(row, 17).value),
                                    'contact_designation': str(
                                        sheet.cell(row, 18).value)
                                },
                                {
                                    'contact_name': str(
                                        sheet.cell(row, 20).value),
                                    'contact_designation': str(
                                        sheet.cell(row, 21).value)
                                }]
                            # assigning existing company to 'data' variable
                            data = company
                        else:
                            sector_row_id = None
                            industry_row_id = None
                            if sector:
                                sector_row_id = sector.row_id
                            if industry:
                                industry_row_id = industry.row_id
                            company_detail = {
                                'identifier': str(
                                    sheet.cell(row, 1).value),
                                'isin_number': str(
                                    sheet.cell(row, 2).value),
                                'sedol': str(sheet.cell(row, 3).value),
                                'permanent_security_identifier':
                                    str(sheet.cell(row, 4).value),
                                'account_type': account_type,
                                'company_name': str(
                                    sheet.cell(row, 5).value),
                                'industry_id': industry_row_id,
                                'sector_id': sector_row_id,
                                'industry_name':
                                    str(sheet.cell(row, 7).value),
                                'sector_name':
                                    str(sheet.cell(row, 8).value),
                                'region': str(sheet.cell(row, 9).value),
                                'country': str(sheet.cell(row, 10).value),
                                'state': str(sheet.cell(row, 11).value),
                                'city': str(sheet.cell(row, 12).value),
                                'address': str(sheet.cell(row, 13).value),
                                'business_desc':
                                    str(sheet.cell(row, 14).value),
                                'website': str(sheet.cell(row, 15).value),
                                'telephone_number': str(sheet.cell(
                                    row, 16).value),
                                'management_profile': [
                                        {
                                            'contact_name': str(
                                                sheet.cell(row, 17).value),
                                            'contact_designation': str(
                                                sheet.cell(row, 18).value)
                                        },
                                        {
                                            'contact_name': str(
                                                sheet.cell(row, 20).value),
                                            'contact_designation': str(
                                                sheet.cell(row, 21).value)
                                        }]}
                            # add new company
                            if (company_detail.get("company_name") != ""):
                                data, errors = CompanySchema().load(
                                    company_detail)
                                if errors:
                                    print(errors)
                                    continue
                                data.created_by = user_id
                                data.updated_by = user_id
                        try:
                            # no errors, add to db
                            db.session.add(data)
                            db.session.commit()
                        except IntegrityError as e:
                            db.session.rollback()
                            continue

        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('Done')
