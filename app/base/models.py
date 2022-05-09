"""
Common functionalities for DB Models, can include classes, functions.
"""

import os
import datetime

from flask import current_app

from app import db


class BaseModel(db.Model):
    """
    Base model for other database tables to inherit, has some common
    functionalities
    """
    __abstract__ = True
    root_folder_key = ''  # configuration key for the root folder of files

    row_id = db.Column('id', db.BigInteger, primary_key=True)
    created_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    modified_date = db.Column(db.DateTime, default=datetime.datetime.utcnow,
                              onupdate=datetime.datetime.utcnow)

    def file_subfolder_name(self):
        """
        By default any related files will be stored in a subfolder with name as
        the 'row_id'
        """
        if self.row_id:
            return str(self.row_id)
        else:
            raise Exception('Model not ready to provide subfolder name')

    def full_folder_path(self, root_key=None):
        """
        Returns the full folder path, minus the main storage folder, so that
        it can be easily reused for both local, and s3 storage.
        :param root_key:
            if passed is used, defaults to 'root_folder_key' attribute
        """

        if not root_key:
            root_key = self.root_folder_key
        return os.path.join(current_app.config[root_key],
                            self.file_subfolder_name())
