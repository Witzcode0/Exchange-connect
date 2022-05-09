"""
Semi documentation related tasks, for each type of parsing file
"""

import os
import glob
import subprocess
import PyPDF2
import datetime

from flask import current_app
from app.common.utils import delete_fs_file, upload_to_s3
from app.semidocument_resources.parsing_files.models import ParsingFile
from flask_script import Command, Option
from app import db
from app.resources.accounts.models import Account

from queueapp.tasks import logger
from queueapp.semi_documentation.pdf_to_csv_parsing import create_class_index


def add_parsing_file(input_path, isin, account_id, ext, *args, **kwargs):
    try:
        os.chdir(input_path)

        for file in glob.glob("*." + ext):
            if '.pdf' in file:
                continue
            try:
                upload_to_s3(
                    os.path.join(input_path, file),
                    os.path.join(
                        current_app.config['PARSING_FILE_FOLDER'], isin, file),
                    bucket_name=current_app.config[
                        'S3_SEMIDOCUMENT_BUCKET'], acl='public-read')
                data = ParsingFile(
                    filename=file,
                    account_id=account_id)
                db.session.add(data)
                db.session.commit()
                delete_fs_file(os.path.join(input_path, file))
            except Exception as e:
                logger.exception(e)
                continue
        if not os.listdir(input_path):
            return True

    except Exception as e:
        logger.exception(e)
        result = False


def convert_pdf_to_page_wise_txt(
        input_path, output_path, file_name, report):
    """
    convert pdf to page wise text file
    :param input_path: input pdf file path
    :param output_path: output storage text path
    :param file_name: filename
    :param report: research report data
    :return:
    """
    # read pdf file
    input_file = open(input_path, 'rb')
    pdfReader = PyPDF2.PdfFileReader(input_file)
    if pdfReader.isEncrypted:
        pdfReader.decrypt('')
    # create parallel parsing file model and uploading s3
    reports = {'research_report_id': report.row_id,
               'account_id': report.account_id,
               'created_by': report.created_by}
    add_parsing_file.s(True, output_path, **reports).delay()
    if pdfReader:
        for i in range(pdfReader.numPages):
            pageObj = pdfReader.getPage(i)
            out_file = os.path.join(
                output_path, file_name.split('.')[0] + '_' + str(i) + '.txt')
            with open(out_file, 'w') as f:
                f.write(pageObj.extractText())
    return


class FileParsing(Command):

    option_list = [
        Option('--verbose', '-v', dest='verbose', action='store_true',
               default=False),
        Option('--dry', '-dry', dest='dry', action='store_true',
               default=False),
        Option('--filepath', '-f', dest='input_file_name', required=True),
        Option('--account_id', '-a', dest='row_id', required=True)
    ]

    def run(self, verbose, dry, row_id, input_file_name, *args, **kwargs):
        try:
            account = Account.query.get(row_id)
            if not account:
                print("account with id {} not found".format(row_id))
                exit(0)
            isin = str(account.isin_number)
            path = os.path.join(
                current_app.config['BASE_DOWNLOADS_FOLDER'], isin)
            if not os.path.exists(path):
                os.mkdir(path)
            txt_file = (path + '/' + str(os.path.basename(
                input_file_name).split('.')[0]) + '.txt')
            command = 'pdftotext ' + input_file_name + " " + txt_file
            subprocess.call(command, shell=True)
            # for html and png parsing
            html_file = (path + '/' + str(os.path.basename(
                input_file_name).split('.')[0]) + '.html')
            command = 'pdftohtml -nodrm -s -c ' + input_file_name + " " + html_file
            subprocess.call(command, shell=True)

            # for csv parsing
            html_path = (path + '/' + str(os.path.basename(
                input_file_name).split('.')[0]) + '-html.html')
            create_class_index(
                html_path, path + '/' + str(os.path.basename(
                    input_file_name).split('.')[0]), True)

            # if all parsing done then pdf file also delete
            # delete_fs_file(html_path)
            # delete_fs_file(html_file)
            # delete_fs_file(input_file_name)
            add_parsing_file(path, isin, row_id, 'txt')
            add_parsing_file(path, isin, row_id, 'pdf')
            add_parsing_file(path, isin, row_id, 'csv')
            add_parsing_file(path, isin, row_id, 'html')
            add_parsing_file(path, isin, row_id, 'png')

        except Exception as e:
            print(e)
            exit(0)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
