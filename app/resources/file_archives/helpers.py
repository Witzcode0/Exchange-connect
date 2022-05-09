import os

from flask import current_app, g
from app.common.utils import get_s3_download_link, do_nothing

from app.resources.file_archives.models import ArchiveFile

def add_logo_url(objs):
    for obj in objs:
        root_config = current_app.config[
                ArchiveFile.root_folder_key]

        if obj['filename']:
            if current_app.config['S3_UPLOAD']:
                signer = get_s3_download_link
            else:
                signer = do_nothing
            obj['file_url'] = signer(os.path.join(
                root_config, str(obj['row_id']), obj['filename']),
                expires_in=3600)