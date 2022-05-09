"""
Semi documentation related tasks, for each type of parsing file
"""

import os
import requests
import datetime
import subprocess
import PyPDF2

from flask import current_app
from sqlalchemy.orm import load_only
from app import db
from app.common.utils import delete_fs_file, upload_to_s3
from app.resources.corporate_announcements.models import CorporateAnnouncement
from app.semidocument_resources.research_reports.models import ResearchReport
from app.semidocument_resources.parsing_files.models import ParsingFile

from queueapp.tasks import celery_app, logger
from queueapp.semi_documentation.pdf_to_csv_parsing import create_class_index


@celery_app.task(bind=True, ignore_result=True)
def parsing_research_report_announcement_file(
        self, result, row_id, announcement_ids, *args, **kwargs):
    """
    Parse pdf file in into text, png, html and csv files and store in s3
    :param self:
    :param result:
    :param row_id: id of research report
    :param announcement_ids: list of ids of corporate announcements
    :param args:
    :param kwargs:
    :return:
    """

    if result:
        try:
            if not row_id:
                return False

            report = ResearchReport.query.filter(
                ResearchReport.row_id == row_id).first()

            if not announcement_ids:
                return False
            announcements = CorporateAnnouncement.query.filter(
                CorporateAnnouncement.row_id.in_(announcement_ids)
            ).options(load_only('row_id', 'file', 'url', 'subject')).all()
            for announcement in announcements:
                path = os.path.join(
                    current_app.config['BASE_DOWNLOADS_FOLDER'], str(
                        report.row_id))
                if not os.path.exists(path):
                    os.mkdir(path)

                announcement.load_urls()
                url = announcement.file_url or announcement.url
                try:
                    if 'pdf' not in url:
                        continue
                    file = requests.get(url)
                    pdf_file_name = ''
                    if announcement.file:
                        pdf_file_name = announcement.file
                    else:
                        pdf_file_name = announcement.subject + '.pdf'
                    input_file_name = (
                        path + '/' + pdf_file_name)
                    with open(input_file_name, 'wb') as f:
                        f.write(file.content)

                    txt_file = (path + '/' + str(os.path.basename(
                        input_file_name).split('.')[0]) + '.txt')
                    command = 'pdftotext ' + input_file_name + " " + txt_file
                    subprocess.call(command, shell=True)

                    # for parsing file entry
                    reports = {'research_report_id': report.row_id,
                               'account_id': report.account_id,
                               'created_by': report.created_by}
                    add_parsing_file.s(True, path, **reports).delay()

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
                    delete_fs_file(html_path)
                    delete_fs_file(html_file)
                    delete_fs_file(input_file_name)
                except Exception as e:
                    logger.exception(e)
                    continue
            result = True
        except Exception as e:
            logger.exception(e)
            result = False

        return result


@celery_app.task(bind=True, ignore_result=True)
def add_parsing_file(self, result, input_path, *args, **kwargs):
    """
    Add parsed file in parsing model and s3 bucket
    :param input_path: path of parsed files
    :return:
    """
    if result:
        try:
            while True:
                for file in os.listdir(input_path):
                    if '.pdf' in file or '.html' in file:
                        continue
                    try:
                        upload_to_s3(
                            os.path.join(input_path, file),
                            os.path.join(
                                current_app.config['PARSING_FILE_FOLDER'],
                                str(kwargs['research_report_id']), file),
                            bucket_name=current_app.config[
                                'S3_SEMIDOCUMENT_BUCKET'], acl='public-read')
                        data = ParsingFile(
                            research_report_id=kwargs['research_report_id'],
                            filename=file,
                            account_id=kwargs['account_id'],
                            created_by=kwargs['created_by'])
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
    return result


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
