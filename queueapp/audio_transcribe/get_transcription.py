import time
import datetime
import os
import boto3
import pandas as pd
from flask import current_app

from app import db
from app.resources.audio_transcribe.models import AudioTranscribe

from queueapp.tasks import celery_app, logger
from app.common.utils import upload_to_s3
from app.resources.audio_transcribe import constants as ATPROGRESS
from queueapp.audio_transcribe.audio_transcript_email_task import send_transcript_link_email


@celery_app.task(bind=True, ignore_result=True)
def transcribe_audio(self, result, row_id, vocab_flag, vocab_name, *args, **kwargs):

    session = boto3.Session(
        aws_access_key_id=current_app.config['TRANSCRIBE_UNAME'],
        aws_secret_access_key=current_app.config['TRANSCRIBE_PWORD'],
    )
    transcribe = session.client('transcribe', region_name=current_app.config['AWS_REGION'])

    if result:
        try:
            model = AudioTranscribe.query.get(row_id)
            if model is None:
                return False

            job_temp = "_".join( model.title.split() )
            tdate = datetime.datetime.now()
            dtimestamp = str(tdate.strftime("%Y%m%d%H%M%S"))
            job_name = job_temp + '_' + dtimestamp
            file_format = model.filename.split('.')[-1]
            url = 'https://{}.s3.{}.amazonaws.com/audiotranscribefile/{}/{}'.format(current_app.config['S3_BUCKET'], current_app.config['AWS_REGION'], row_id, model.filename)
            # job_uri = 'https://csconferencecall.s3.ap-south-1.amazonaws.com/Century-2.wav'
            if vocab_flag:
                transcribe.start_transcription_job(
                    TranscriptionJobName=job_name,
                    Media={'MediaFileUri': url},
                    MediaFormat=file_format,
                    LanguageCode='en-IN',
                    Settings={
                        'VocabularyName': vocab_name}
                )
            else:
                transcribe.start_transcription_job(
                    TranscriptionJobName=job_name,
                    Media={'MediaFileUri': url},
                    MediaFormat=file_format,
                    LanguageCode='en-IN')

            while True:
                status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
                if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
                    break
                print("Not ready yet...")
                time.sleep(30)

            #filefolder
            path = os.path.join(
                current_app.config['BASE_AUDIO_TRANSCRIBE_FOLDER'])
            if not os.path.exists(path):
                os.makedirs(path)
            filename = job_temp + '.txt'
            filepath = os.path.join(path, filename)

            #get transcription and upload text file on s3
            if status['TranscriptionJob']['TranscriptionJobStatus'] == "COMPLETED":

                data = pd.read_json(status['TranscriptionJob']['Transcript']['TranscriptFileUri'])
                print(data['results'][1][0]['transcript'])
                with open(filepath, 'w') as file:
                    file.write(data['results'][1][0]['transcript'])
                    file.close()
                upload_to_s3(filepath, os.path.join(current_app.config['AUDIO_TRANSCRIBE_FILE_FOLDER'],
                                str(row_id), filename), bucket_name=current_app.config['S3_BUCKET'], acl='public-read')

                send_transcript_link_email.s(True, row_id).delay()

                try:
                    AudioTranscribe.query.filter(
                        AudioTranscribe.row_id == model.row_id).update(
                        {AudioTranscribe.progress: ATPROGRESS.AT_COMPLETED,
                         AudioTranscribe.transcript_job_name: job_name},
                        synchronize_session=False)
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    print(e)
                return True
            elif status['TranscriptionJob']['TranscriptionJobStatus'] == "FAILED":
                try:
                    AudioTranscribe.query.filter(
                        AudioTranscribe.row_id == model.row_id).update(
                        {AudioTranscribe.progress: ATPROGRESS.AT_FAILED},
                        synchronize_session=False)
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    print(e)
                return False

        except Exception as e:
            logger.exception(e)
            try:
                AudioTranscribe.query.filter(
                    AudioTranscribe.row_id == row_id).update(
                    {AudioTranscribe.err_msg: str(e)},
                    synchronize_session=False)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(e)
            result = False
    return result
