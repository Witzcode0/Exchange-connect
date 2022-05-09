import urllib.parse
import os
import re
import boto3
import time
from flask import current_app
from app.common.utils import get_s3_download_link
from app.base import constants as APP
from app.resources.audio_transcribe import constants as ATPROGRESS
from app.domain_resources.domains.helpers import get_domain_info
from app.resources.accounts.models import Account
from app.resources.account_profiles.models import AccountProfile
from app.resources.management_profiles.models import ManagementProfile


def generate_transcript_email_link(transcript_model):
    temp_title = "_".join(transcript_model.title.split())
    if current_app.config['S3_UPLOAD']:
        signer = get_s3_download_link

        url = signer(os.path.join(
            current_app.config['AUDIO_TRANSCRIBE_FILE_FOLDER'],
            str(transcript_model.row_id), temp_title + '.txt'), expires_in=36000)

        print("url --->", url)

        return url
    else:
        return None


def delete_transcription_job(result, job_name):
    session = boto3.Session(
        aws_access_key_id=current_app.config['TRANSCRIBE_UNAME'],
        aws_secret_access_key=current_app.config['TRANSCRIBE_PWORD'],
    )
    transcribe = session.client('transcribe', region_name=current_app.config['AWS_REGION'])

    if result:
        try:
            response = transcribe.delete_transcription_job(
                TranscriptionJobName=job_name
            )
            print(response)
        except Exception as e:
            print(e)
    return True


def generate_vocab(account_id, custom_name):
    session = boto3.Session(
        aws_access_key_id=current_app.config['TRANSCRIBE_UNAME'],
        aws_secret_access_key=current_app.config['TRANSCRIBE_PWORD'],
    )
    transcribe = session.client('transcribe', region_name=current_app.config['AWS_REGION'])

    account_query = Account.query.filter(
                    Account.row_id == account_id).first()
    aprofile_id = AccountProfile.query.filter(
                    AccountProfile.account_id == account_id).first()
    manament_pquery = ManagementProfile.query.filter(
                    ManagementProfile.account_profile_id == aprofile_id.row_id).all()

    a_keywords = account_query.keywords
    m_names = [x.name for x in manament_pquery]
    m_designation = [x.designation for x in manament_pquery]

    temp_vocab = a_keywords + m_names + m_designation
    s = [(re.sub(r'[^\w\s]', '', x)) for x in temp_vocab]
    s = [(re.sub(r'\s+', '', text)) for text in s]
    phrase = list(set(s))

    phrases = [x.replace(' ', '-') for x in phrase]
    try:
        transcribe.create_vocabulary(
            VocabularyName=custom_name,
            LanguageCode='en-IN',
            Phrases=phrases)

        while True:
            status = transcribe.get_vocabulary(VocabularyName=custom_name)
            if status['VocabularyState'] in ['READY', 'FAILED']:
                break
            print("Not ready yet...")
            time.sleep(30)

        if status['VocabularyState'] == 'READY':
            return True
        elif status['VocabularyState'] == 'FAILED':
            return False
    except Exception as e:
        print(e)
        return False
