import datetime
import os

from flask_script import Command, Option
from flask import current_app

from app import db
from app.resources.management_profiles.models import ManagementProfile
from app.common.helpers import upload_file
from app.common.utils import delete_fs_file, generate_thumbnail, get_s3_file


class UpdateManagementProfileThumbnails(Command):
    """
    Command to update management profile thumbnail

    :arg verbose: print progress
    :arg dry:
        dry run
    """

    option_list = [
        Option('--verbose', '-v', dest='verbose', action='store_true',
               default=False),
        Option('--dry', '-dry', dest='dry', action='store_true',
               default=False),
        Option('--destination_file_path', '-destination_file_path',
               dest='destination_file_path', required=True),
        Option('--page', '-page', dest='page', type=int),
        Option('--width', '-width', dest='width', type=int),
        Option('--height', '-height', dest='height', type=int),

    ]

    def run(self, verbose, dry, destination_file_path, page, width, height):
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('Updating management profile thumbnail')

        try:
            management_profiles = ManagementProfile.query.all()
            for management_profile in management_profiles:
                # create thumbnail full path
                thumbnail_full_folder = management_profile.full_folder_path(
                    ManagementProfile.root_profile_photo_folder_key)
                management_profile.load_urls()
                # if profile photo is there but thumbnail is not generated
                if management_profile.profile_photo_url and \
                    not management_profile.profile_thumbnail_url:
                    # for s3 source file
                    s3_source_file = os.path.join(
                        management_profile.full_folder_path(
                            ManagementProfile.root_profile_photo_folder_key),
                        management_profile.profile_photo)
                    # download destination path
                    download_dest_path = os.path.join(
                        management_profile.full_folder_path(
                            ManagementProfile.root_profile_photo_folder_key),
                        management_profile.profile_photo)
                    # download file from s3
                    get_s3_file(s3_source_file, download_dest_path)

                    if current_app.config['S3_UPLOAD']:
                        # create thumbnail
                        fpath = generate_thumbnail(
                            download_dest_path, destination_file_path,
                            page, width, height)
                        # upload in s3
                        if not upload_file(
                                fpath, thumbnail_full_folder,
                                bucket_name=current_app.config[
                                    'S3_THUMBNAIL_BUCKET'],
                                acl='public-read'):
                            print('Could not upload file')
                            continue
                        # update profile thumbnail
                        management_profile.profile_thumbnail = os.path.basename(
                            fpath)
                        db.session.commit()
                        # delete from local
                        delete_fs_file(fpath)
                    delete_fs_file(download_dest_path)
            
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
