import datetime
import mimetypes

from xlrd import open_workbook
from flask_script import Command, Option

from app import db
from app.esg_framework_resources.esg_parameters.schemas import (
    ESGParameterSchema)
from app.base.constants import FILE_TYPES


class ImportESGParametersByExcel(Command):
    """
    Command to import esg parameters data from xlsx file

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
        Option('--xls_file', '-xls', dest='xls_file', required=True),
    ]

    def run(self, verbose, dry, user_id, xls_file):
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('Adding esg parameters')
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
                main_index = 0
                main_parent_id = None
                company_wb = open_workbook(xls_file)
                for sheet in company_wb.sheets():
                    if 'General Questions' in sheet.name:
                        continue
                    else:
                        main_index += 1
                        main_parent_id, errors = load_esg_paramenter_data(
                            sheet.name.strip(), None, str(main_index), user_id)

                        if errors:
                            main_index -= 1
                            continue

                        sub_index = 0
                        child_index = 0
                        for row in range(2, sheet.nrows):
                            if sheet.cell(row, 0).value:
                                sub_index += 1
                                index = str(main_index) + '.' + str(sub_index)
                                sub_parent_id, errors = load_esg_paramenter_data(
                                    sheet.cell(row, 1).value.strip(), main_parent_id,
                                    index, user_id)
                                if errors:
                                    sub_index -= 1
                                    continue
                                child_index = 0
                            else:
                                child_index += 1
                                index = str(main_index) + '.' + str(sub_index) + \
                                        '.' + str(child_index)
                                child_parent_id, errors = load_esg_paramenter_data(
                                    sheet.cell(row, 1).value.strip(), sub_parent_id,
                                    index, user_id)
                                if errors:
                                    child_index -= 1
                                    continue
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')

def load_esg_paramenter_data(name, parent_id, parameter_index, user_id):
    """
    Insert data in ESG Parameter data
    :param name: name of parameter
    :param parent_id: parent id
    :param parameter_index: parameter index
    :return: parent id and errors
    """
    parameter_schema = ESGParameterSchema()
    esg_parameters = {
        'name': name,
        'parameter_index': parameter_index,
        'parameter_parent_id': parent_id}

    data, errors = parameter_schema.load(esg_parameters)
    if errors:
        return None, errors
    data.created_by = user_id
    data.updated_by = user_id
    data.parameter_sort_index = data.generate_sort_index()
    db.session.add(data)
    db.session.commit()

    return data.row_id, None
