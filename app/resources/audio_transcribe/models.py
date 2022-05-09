"""
Models for "audio transcribe" package.
"""
import os

from flask import current_app
from sqlalchemy import func, Index
from sqlalchemy import UniqueConstraint

from app.common.utils import get_s3_download_link, do_nothing
from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString
from app.base.model_fields import ChoiceString
from app.resources.audio_transcribe import constants as ATPROGRESS


class AudioTranscribe(BaseModel):

    __tablename__ = 'audio_transcribe'

    root_file_folder_key = 'AUDIO_TRANSCRIBE_FILE_FOLDER'

    title = db.Column(db.String(128), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'),
                           nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'),
                           nullable=False)
    filename = db.Column(db.String())
    email = db.Column(LCString(128), nullable=False)
    progress = db.Column(ChoiceString(ATPROGRESS.AT_PROGRESS_TYPE_CHOICES),
                             nullable=False, default=ATPROGRESS.AT_PENDING)
    err_msg = db.Column(db.String())
    email_status = db.Column(db.Boolean, default=False)
    acc_id = db.Column(db.Integer, db.ForeignKey('account.id'),
                           nullable=True)
    transcript_job_name = db.Column(db.String())

    # dynamic properties
    file_url = None
    transcript_url = None

    __table_args__ = (
        # unique lower case index, i.e case-insensitive unique constraint
        Index('audio_transcribe_unique_title', func.lower(title),
              unique=True),
    )

    # relationships
    account = db.relationship('Account', backref=db.backref(
        'audio_account_id', lazy='dynamic'))

    def __init__(self, row_id=None, *args, **kwargs):
        self.row_id = row_id
        super(AudioTranscribe, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<AudioTranscribe %r>' % (self.row_id)

    def load_urls(self, with_redirect=False, expires_in=3600):
        """
        Populates the file_url dynamic properties
        """

        if (not self.filename and not self.title):
            return
        sub_folder = self.file_subfolder_name()
        if current_app.config['S3_UPLOAD']:
            signer = get_s3_download_link
        else:
            signer = do_nothing
        if self.filename:
            self.file_url = signer(os.path.join(
                current_app.config[self.root_file_folder_key],
                sub_folder, self.filename), expires_in=expires_in)
        if self.title:
            if self.progress == ATPROGRESS.AT_COMPLETED:
                temp_title = "_".join( self.title.split() )
                self.transcript_url = signer(os.path.join(
                    current_app.config[self.root_file_folder_key],
                    sub_folder, temp_title + '.txt'), expires_in=expires_in)
        return
