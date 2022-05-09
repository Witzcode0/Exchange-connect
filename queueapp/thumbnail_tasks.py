"""
Thumbnail related tasks
"""

import os

from fnmatch import fnmatch
from flask import current_app

from app import db
from queueapp.tasks import celery_app, logger
from app.base import constants as APP
from app.common.helpers import upload_file
from app.common.utils import delete_fs_file, generate_thumbnail
from app.resources.event_file_library.models import EventLibraryFile
from app.resources.company_page_file_library.models import (
    CompanyPageLibraryFile)
from app.resources.post_file_library.models import PostLibraryFile
from app.resources.file_archives.models import ArchiveFile
from app.resources.user_profiles.models import UserProfile
from app.resources.account_profiles.models import AccountProfile
from app.newswire_resources.newswire_post_file_library.models import (
    NewswirePostLibraryFile)
from app.crm_resources.crm_contacts.models import CRMContact
from app.crm_resources.crm_file_library.models import CRMLibraryFile
from app.resources.management_profiles.models import ManagementProfile
from app.semidocument_resources.research_reports.models import ResearchReport
from app.resources.ir_module.models import IrModule


@celery_app.task(bind=True, ignore_result=True)
def convert_file_into_thumbnail(self, result, row_id, module, filepath,
                                *args, **kwargs):
    """
    Convert general files into thumbnail, general files such
    as images, docx, pdf etc.
    :param row_id: the row_id of data for thumbnail
    :param module: describe which module's file convert into thumbnail such as
        (event, post, file_archive, user_profile, account_profile,
         newswire_post_file_library)
    :param filepath: file path for convert into thumbnail
    """
    if result:
        model = None
        error = None
        data = None
        try:
            if module == APP.MOD_EVENT:
                model = EventLibraryFile
                data = EventLibraryFile.query.get(row_id)
                if not data:
                    return True
            elif module == APP.MOD_POST:
                model = PostLibraryFile
                data = PostLibraryFile.query.get(row_id)
                if not data:
                    return True
            elif module == APP.MOD_ARCHIVE:
                model = ArchiveFile
                data = ArchiveFile.query.get(row_id)
                if not data:
                    return True
            elif module == APP.MOD_ACCOUNT_PROFILE:
                model = AccountProfile
                data = AccountProfile.query.get(row_id)
                if not data:
                    return True
            elif module == APP.MOD_USER_PROFILE:
                model = UserProfile
                data = UserProfile.query.get(row_id)
                if not data:
                    return True
            elif module == APP.MOD_NEWSWIRE_POST_FILE_LIBRARY:
                model = NewswirePostLibraryFile
                data = NewswirePostLibraryFile.query.get(row_id)
                if not data:
                    return True
            elif module == APP.MOD_CRM_CONTACT_PROFILE:
                model = CRMContact
                data = CRMContact.query.get(row_id)
                if not data:
                    return True
            elif module == APP.MOD_COMPANY:
                model = CompanyPageLibraryFile
                data = CompanyPageLibraryFile.query.get(row_id)
                if not data:
                    return True
            elif module == APP.MOD_CRM_FILE_LIBRARY:
                model = CRMLibraryFile
                data = CRMLibraryFile.query.get(row_id)
                if not data:
                    return True
            elif module == APP.MOD_MGMT_PROFILE:
                model = ManagementProfile
                data = ManagementProfile.query.get(row_id)
                if not data:
                    return True
            elif module == APP.MOD_RESEARCH_REPORT:
                model = ResearchReport
                data = ResearchReport.query.get(row_id)
                if not data:
                    return True
            elif module == APP.MOD_IR_MODULE_PHOTO:
                model = IrModule
                data = IrModule.query.get(row_id)
                if not data:
                    return True

            if 'cover' in args:
                thumbnail_full_folder = data.full_folder_path(
                    model.root_cover_photo_folder_key)
            elif 'profile' in args:
                thumbnail_full_folder = data.full_folder_path(
                    model.root_profile_photo_folder_key)
            else:
                thumbnail_full_folder = data.full_folder_path(
                    model.root_folder_key)

            file_data = {'files': {}}

            fpath = generate_thumbnail(filepath, thumbnail_full_folder)

            if current_app.config['S3_UPLOAD']:
                if not upload_file(
                        fpath, thumbnail_full_folder,
                        bucket_name=current_app.config['S3_THUMBNAIL_BUCKET'],
                        acl='public-read'):
                    error = 'Could not upload file'

                if error:
                    return True
                delete_fs_file(fpath)

            fname = os.path.basename(fpath)

            file_data['files'][fname] = fpath

            if file_data['files']:
                if 'cover' in args:
                    data.cover_thumbnail = [
                        fname for fname in file_data['files']][0]
                elif 'profile' in args:
                    data.profile_thumbnail = [
                        fname for fname in file_data['files']][0]
                else:
                    data.thumbnail_name = [
                        fname for fname in file_data['files']][0]

            db.session.add(data)
            db.session.commit()
            # delete normal file form local
            delete_fs_file(filepath)
            # delete extra pdf file from common thumbnail folder
            for dirpath, dirnames, filenames in os.walk(
                    os.path.dirname(fpath)):
                for file in filenames:
                    if fnmatch(file, '*.pdf'):
                        os.remove(os.path.join(dirpath, file))
            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

        return result
