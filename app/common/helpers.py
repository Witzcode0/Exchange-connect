"""
Add any common helper functions/classes here.
"""

from datetime import datetime as dt

import os
import mimetypes
import urllib.parse
import json
import shutil
import uuid
import pytz

from flask import current_app
from flask_uploads import UploadNotAllowed
from icalendar import Calendar, Event, vCalAddress, vText

from app import db
from app.common.utils import (
    upload_to_s3, delete_fs_file, delete_from_s3, get_payload_from_value,
    get_value_from_payload, copy_s3_to_s3, calling_bigmarker_apis,
    time_converter)
from app.base import constants as APP
from app.webinar_resources.webinars.models import Webinar
from app.webinar_resources.webinar_invitees.models import WebinarInvitee
from app.webcast_resources.webcasts.models import Webcast
from app.webcast_resources.webcast_invitees.models import WebcastInvitee
from app.toolkit_resources.project_e_meeting.models import Emeeting
from app.toolkit_resources.project_e_meeting_invitee.models import (
    EmeetingInvitee)
from app.domain_resources.domains.helpers import get_domain_info


def save_files_locally(upload_set, storage, sub_folder=None, name=None):
    """
    Saves a file in local filesystem, can raise errors
    """
    fpath, fname, error = '', '', ''
    try:
        fname = upload_set.save(storage, folder=sub_folder, name=name)
        fpath = upload_set.path(fname)
    except UploadNotAllowed:
        e = 'File type not allowed'
        current_app.logger.exception(e)
        error = e
    except Exception as e:
        current_app.logger.exception(e)
        error = e
    return fpath, fname, error


def upload_file(source_file, folder, bucket_name='', acl='private'):
    """
    Uploads the file to S3
    """
    # if file store locally
    if acl == 'public-read':
        bucket_name = current_app.config['S3_THUMBNAIL_BUCKET']
    destination = os.path.join(folder, os.path.basename(source_file))
    return upload_to_s3(
        source_file, destination, bucket_name=bucket_name, acl=acl)


def store_file(upload_set, storage, sub_folder=None, full_folder=None,
               name=None, basename_only=True, detect_type=False,
               type_only=False, acl='private', **kwargs):
    """
    Stores a file locally, and into a different data store, incase those
    kwargs are provided
    """
    fpath, fname, error = save_files_locally(
        upload_set, storage, sub_folder=sub_folder, name=name)
    if basename_only:
        fname = os.path.basename(fname)
    if not error:
        if current_app.config['S3_UPLOAD']:
            if not upload_file(fpath, full_folder, acl=acl):
                error = 'Could not upload file'
            # delete local copy irrespective of success failure of upload
            if 'not_local' not in kwargs:
                delete_fs_file(fpath)

    if error:
        error = {'message': error, 'code': 422}

    if detect_type:
        # detect the type and return
        file_type = ''
        if error:
            return fpath, fname, error, file_type
        file_type = mimetypes.guess_type(fpath)[0]
        if type_only and file_type and '/' in file_type:
            file_type = file_type.split('/')[1]

        return fpath, fname, error, file_type

    return fpath, fname, error


def copy_file_locally(full_folder, dest_path, f_name):
    """
    copies the files locally
    :param full_folder
        the source folder, to be joined with base_folder and file_name\
        to get absolute source path
    :param dest_path
        the destination folder, to be joined with base_folder to get\
        absolute destination path
    :param f_name
        file_name of the file to be copied
    """
    src_path = os.path.join(
        current_app.config['BASE_UPLOADS_FOLDER'],
        full_folder, str(f_name))
    full_dest_path = os.path.join(
        current_app.config['BASE_UPLOADS_FOLDER'],
        dest_path)
    try:
        if not os.path.exists(full_dest_path):
            os.makedirs(full_dest_path)
        shutil.copy(src_path, full_dest_path)
    except Exception as e:
        pass
    return


def delete_files(
        names, sub_folder=None, full_folder=None, is_thumbnail=False,
        **kwargs):
    """
    Deletes a list of files from data store, and locally
    :param names: list of file names for deleting from local and s3
    :param sub_folder: sub folder path
    :param full_folder: full folder path
    :param is_thumbnail: to identify s3 bucket for thumbnail or normal file
    """
    keys = [os.path.join(full_folder, os.path.basename(name))
            for name in names]
    error = ''

    if current_app.config['S3_UPLOAD']:
        # for thumbnail file delete
        if is_thumbnail:
            error = not delete_from_s3(
                keys, bucket_name=current_app.config['S3_THUMBNAIL_BUCKET'])
        else:
            error = not delete_from_s3(keys)

    if not error:
        # delete local copy of file(s)
        # thumbnails are already deleted after generation
        if not is_thumbnail:
            for fk in keys:
                fpath = os.path.join(
                    current_app.config['BASE_UPLOADS_FOLDER'], fk)
                delete_fs_file(fpath)

    if error:
        error = {'message': 'Could not delete file(s)', 'code': 422}

    return error


def copy_file_s3_to_s3(full_folder, dest_path, sub_folder, f_name,
                       bucket_name=''):
    """
    copies the files from s3 to s3
    #TODO: fix, not working

    :param full_folder
        the source folder, to be joined with base_folder and file_name\
        to get absolute source path
    :param dest_path
        the destination folder, to be joined with base_folder to get\
        absolute destination path
    :param sub_folder
        source sub_folder name
    :param f_name
        file_name of the file to be copied
    :param bucket_name:
        the bucket name
    """
    bucket_name = current_app.config['S3_BUCKET']
    aws_dest_path = dest_path.split("/")[-2]
    aws_src_path_key = os.path.join(full_folder, str(f_name))
    try:
        copy_s3_to_s3(os.path.join(
            bucket_name, aws_dest_path, sub_folder, f_name),
            aws_src_path_key, f_name)
    except Exception as e:
        pass
    return


def copy_file(full_folder, dest_path, sub_folder, f_name):
    """
    copies the files locally and/or s3 to s3
    """
    try:
        copy_file_locally(full_folder, dest_path, f_name)
        copy_file_s3_to_s3(full_folder, dest_path, sub_folder,
                           f_name)
    except Exception as e:
        pass

    return


def file_type_for_thumbnail(filename):
    """
    Decide file type for normal file to convert thumbnail
    """
    fmtype = (os.path.basename(filename)).split('.')[-1]
    if fmtype in APP.FOR_THUMBNAIL:
        return True


def generate_video_email_link(add_url, video_type,
                              payload='', video_model=None, domain_name = None):
    """
    Function that generates watch demo/teaser video link

    :param add_url:
        the additional url which will be used
    :param video_type:
        the type of the video demo or teaser

    :return url:
        returns the event book link.
    """
    domain_name = 's-ancial.com'
    if payload:
        payload = '?' + 'token=' + str(payload)
    if domain_name:
        domain_name = domain_name
    else:
        if video_model:
            domain_name = video_model.account.domain.name
    domain_id, domain_config = get_domain_info(domain_name)

    if video_type == APP.VID_TEASER:
        url = urllib.parse.urljoin(
            domain_config['FRONTEND_DOMAIN'],
            ''.join([add_url, urllib.parse.quote_plus(''.join(
                [str(APP.VID_TEASER)]).encode('utf8')), payload]))

        print("url is here: ",url)
    elif video_type == APP.VID_DEMO:
        url = urllib.parse.urljoin(
            domain_config['FRONTEND_DOMAIN'],
            ''.join([add_url, urllib.parse.quote_plus(''.join(
                [str(APP.VID_DEMO)]).encode('utf8')), payload]))
    else:
        url=None
    return url

def generate_event_book_email_link(
        add_url, event_model, event_type=None, payload='',
        guest_event_path=None, domain_name = None):
    """
    Function that generates the book now event link or
    survey participation link.

    :param add_url:
        the additional url which will be used
    :param event_model:
        the id of the event or survey

    :return url:
        returns the event book link.
    """
    if payload:
        payload = '&' + 'token=' + str(payload)
    if domain_name:
        domain_name = domain_name
    else:
        domain_name = event_model.account.domain.name
    domain_id, domain_config = get_domain_info(domain_name)
    if event_type == APP.EVNT_SURVEY or event_type == APP.EVNT_PUBLIC_WEBINAR:
        url = urllib.parse.urljoin(
            domain_config['FRONTEND_DOMAIN'],
            ''.join([add_url, urllib.parse.quote_plus(''.join(
                [str(event_model.row_id)]).encode('utf8')), payload]))
    else:
        path = None
        if guest_event_path:
            path = guest_event_path
        else:
            path = current_app.config['BASE_EVENT_JOIN_PATH']
        url = urllib.parse.urljoin(
            domain_config['FRONTEND_DOMAIN'],
            ''.join([path,
                     urllib.parse.quote_plus(
                         ''.join([add_url, str(event_model.row_id)]
                                 ).encode('utf8')), payload]))
    return url

def generate_bse_announcement_email_link(
        add_url, event_model, event_type=None, payload='',
        guest_event_path=None, domain_name = None):
    """
    Function that generates the book now event link or
    survey participation link.

    :param add_url:
        the additional url which will be used
    :param event_model:
        the id of the event or survey

    :return url:
        returns the event book link.
    """
    if payload:
        payload = '&' + 'token=' + str(payload)
    if domain_name:
        domain_name = domain_name
    else:
        domain_name = 's-ancial.com'
    url = ''
    domain_id, domain_config = get_domain_info(domain_name)
    if event_type == APP.EVNT_BSE_FEED:
        url = urllib.parse.urljoin(
            domain_config['FRONTEND_DOMAIN'],
            ''.join([add_url, urllib.parse.quote_plus(''.join(
                [str(event_model.row_id)]).encode('utf8')), payload]))
    return url


def generate_video_email_link(add_url, video_type,
                              payload='', video_model=None, domain_name = None):
    """
    Function that generates watch demo/teaser video link

    :param add_url:
        the additional url which will be used
    :param video_type:
        the type of the video demo or teaser

    :return url:
        returns the event book link.
    """
    domain_name = 's-ancial.com'
    if payload:
        payload = '?' + 'token=' + str(payload)
    if domain_name:
        domain_name = domain_name
    else:
        if video_model:
            domain_name = video_model.account.domain.name
    domain_id, domain_config = get_domain_info(domain_name)

    if video_type == APP.VID_TEASER:
        url = urllib.parse.urljoin(
            domain_config['FRONTEND_DOMAIN'],
            ''.join([add_url, urllib.parse.quote_plus(''.join(
                [str(APP.VID_TEASER)]).encode('utf8')), payload]))

        print("url is here: ",url)
    elif video_type == APP.VID_DEMO:
        url = urllib.parse.urljoin(
            domain_config['FRONTEND_DOMAIN'],
            ''.join([add_url, urllib.parse.quote_plus(''.join(
                [str(APP.VID_DEMO)]).encode('utf8')), payload]))
    else:
        url=None
    return url


def generate_bse_announcement_email_link(
        add_url, event_model, event_type=None, payload='',
        guest_event_path=None, domain_name = None):
    """
    Function that generates the book now event link or
    survey participation link.

    :param add_url:
        the additional url which will be used
    :param event_model:
        the id of the event or survey

    :return url:
        returns the event book link.
    """
    if payload:
        payload = '&' + 'token=' + str(payload)
    if domain_name:
        domain_name = domain_name
    else:
        domain_name = 'exchangeconnect.in'
    url = ''
    domain_id, domain_config = get_domain_info(domain_name)
    print('Doamin name, id: ', domain_name, domain_id)
    if event_type == APP.EVNT_BSE_FEED:
        url = urllib.parse.urljoin(
            domain_config['FRONTEND_DOMAIN'],
            ''.join([add_url, urllib.parse.quote_plus(''.join(
                [str(event_model.row_id)]).encode('utf8')), payload]))
    return url


def generate_event_book_token(invitee_obj, event_type):
    """
    Generate token for event verification
    """
    event_json = {}
    if event_type == APP.EVNT_CA_EVENT:
        event_json["event_id"] = invitee_obj.corporate_access_event_id
    elif event_type == APP.EVNT_SURVEY:
        event_json["event_id"] = invitee_obj.survey_id
    elif event_type == APP.EVNT_WEBCAST:
        event_json["event_id"] = invitee_obj.webcast_id
    event_json["invite_id"] = invitee_obj.row_id
    event_json["event_type"] = event_type

    return get_payload_from_value(event_json)


def verify_event_book_token(token, event_type):
    """
    Generate value from token
    """
    event_data = None
    try:
        event_data = get_value_from_payload(token).replace('\'', '"')
        event_data = json.loads(event_data)
        if ('event_id' not in event_data or
                'invite_id' not in event_data or
                'event_type' not in event_data or event_data['event_type'] !=
                event_type):
            event_data = None
    except Exception as e:
        event_data = None
    return event_data


def generate_video_token(invitee_obj, video_type):
    """
    generate token for video verification
    """
    video_json = {}
    if 'account_id' in invitee_obj:
        video_json["account_id"] = invitee_obj["account_id"]
    elif invitee_obj.account_id:
        video_json["account_id"] = invitee_obj.account_id
    if 'email' in invitee_obj:
        video_json["email"] = invitee_obj["email"]
    elif invitee_obj.row_id:
        video_json["email"] = invitee_obj.email
    video_json["video_type"] = video_type

    return get_payload_from_value(video_json)


def generate_video_email_token(invitee_obj, video_type):
    """
    generate token for video verification
    """
    video_json = {}
    video_json["account_id"] = invitee_obj.account_id
    video_json["email"] = invitee_obj.email
    video_json["video_type"] = video_type

    return get_payload_from_value(video_json)


def verify_video_token(token):
    """
    Generate value from token
    """
    video_data = None
    try:
        video_data = get_value_from_payload(token).replace('\'', '"')
        video_data = json.loads(video_data)
        # if ('video_id' not in video_data or
        #         'email' not in video_data or
        #         'video_type' not in video_data or video_data['video_type'] !=
        #         video_type):
        #     video_data = None
        if ('email' not in video_data or
                'account_id' not in video_data or
                'video_type' not in video_data):
            video_data = None
    except Exception as e:
        video_data = None
    return video_data



def add_update_conference(data):
    """
    call bigmarker third party api.
    create conference by adding conference_id and urls to db.
    update conference if exists by check with conference_id.
    generate admin url for admin access.

    REQUEST_URL = 'https://www.bigmarker.com/api/v1/' (check in config)

    :param row_id: row_id of webinar or webcast
    :param module: webcast or webinar
    :return:
    """

    response = {'status': False, 'response': {}, 'conference_id': ''}

    try:
        exit_url = ''
        if isinstance(data, Webinar) or isinstance(data, Webcast):
            if isinstance(data, Webinar):
                exit_url = generate_event_book_email_link(
                    current_app.config['WEBINAR_EVENT_JOIN_ADD_URL'],
                    data)
            elif isinstance(data, Webcast):
                exit_url = generate_event_book_email_link(
                    current_app.config['WEBCAST_EVENT_JOIN_ADD_URL'],
                    data)
            started_at = dt.strftime(
                time_converter(data.started_at), '%Y-%m-%d %H:%M')
            duration = data.ended_at - data.started_at
            duration_minutes = str(int(duration.total_seconds() / 60))
            title = data.title
            purpose = data.description
            payload = {
                'duration': duration_minutes,
                'title': data.title,
                'purpose': data.description}

        elif isinstance(data, Emeeting):
            exit_url = generate_event_book_email_link(
                current_app.config['EMEETING_EVENT_JOIN_ADD_URL'],
                data)

            started_at = dt.strftime(
                time_converter(data.meeting_datetime), '%Y-%m-%d %H:%M')
            title = data.meeting_subject
            purpose = data.meeting_agenda
            payload = {
                'title': data.meeting_subject,
                'purpose': data.meeting_agenda}

        payload.update({
            'channel_id': current_app.config['BIGMARKER_CHANNEL_ID'],
            'start_time': str(started_at),
            'exit_url': exit_url,
            'time_zone': 'Mumbai',
            'privacy': 'private',
            'schedule_type': 'one_time',
            'enable_knock_to_enter': False,
            'send_reminder_emails_to_presenters': False,
            'registration_conf_emails': False,
            'send_cancellation_email': False,
            'show_reviews': False,
            'review_emails': False,
            'poll_results': False,
            'enable_ie_safari': True,
            'enable_twitter': False,
            'auto_invite_all_channel_members': False,
            'who_can_watch_recording': 'channel_admin_only',
            'registration_required_to_view_recording': False})

        # if already conference created, so put api will be call
        if data.conference_id:
            sub_url = 'conferences/' + data.conference_id
            bigmarkar_response = calling_bigmarker_apis(
                sub_url=sub_url, json_data=payload, method='put')
        else:
            sub_url = 'conferences/'
            bigmarkar_response = calling_bigmarker_apis(
                sub_url=sub_url, json_data=payload, method='post')

        if not bigmarkar_response.ok:
            response['status'] = False
            response['response'] = json.loads(bigmarkar_response.text)
            return response

        response_data = bigmarkar_response.json()

        # if all good
        admin_object = {}
        conference_id = None
        if 'id' in response_data and response_data['id']:
            conference_id = response_data['id']
            data.conference_id = conference_id
            admin_object['conference_id'] = conference_id
        if ('conference_address' in response_data and
                response_data['conference_address']):
            data.url = response_data['conference_address']
        if 'presenters' in response_data and response_data['presenters']:
            for presenter in response_data['presenters']:
                if presenter['presenter_url']:
                    data.presenter_url = presenter['presenter_url']
                if 'member_id' in presenter and presenter['member_id']:
                    member_id = presenter['member_id']
                    admin_object['bmid'] = member_id
        # call admin api for admin url
        if admin_object:
            admin_url = (
                'conferences/' + admin_object['conference_id'] +
                '/admin_url' + '?bmid=' + admin_object['bmid'])
            admin_response = calling_bigmarker_apis(
                sub_url=admin_url, method='get')
            admin_data = admin_response.json()
            if not admin_data:
                pass
            elif 'admin_url' in admin_data and admin_data['admin_url']:
                data.admin_url = admin_data['admin_url']
        db.session.add(data)
        db.session.commit()
        response['conference_id'] = conference_id
        response['status'] = True
    except Exception as e:
        current_app.logger.exception(e)
        response['status'] = False

    return response


def delete_conference(data=None, conference_id=''):
    """
    When invitee register particular webcast so bigmarker conference
    regitration for particular invitee
    :return: response
    """
    response = {'status': False, 'response': {}}

    try:
        if data:
            conference_id = data.conference_id
            data.conference_id, data.url = None, None
            data.presenter_url, data.admin_url = None, None
            db.session.add(data)
            db.session.commit()
        sub_url = 'conferences/' + conference_id
        bigmarker_response = calling_bigmarker_apis(
            sub_url=sub_url, method='delete')

        if not bigmarker_response.ok:
            response_content = bigmarker_response.content.decode(
                'utf8').replace("'", '"')
            response['status'] = False
            response['response'] = json.loads(response_content)
            return response

        response['status'] = True
    except Exception as e:
        current_app.logger.exception(e)
        response['status'] = False

    return response


def add_response_headers(response):
    """This method the headers passed in to the response"""
    if not current_app.config['DEBUG']:
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        # response.headers['Content-Type'] = 'text/html; charset=utf8'
        response.headers['Strict-Transport-Security'] = \
            'max-age=31536000; includeSubDomains; preload;'
        # response.headers['Content-Security-Policy'] = \
        #     "default-src 'self'; font-src ;img-src data:; script-src ; " \
        #     "style-src ;"
        response.headers['Referrer-Policy'] = "strict-origin"

    return response


def generate_ics_file(summery, dtstart, category=None, dtend=None,
                      location=None, description=None):
    """
    Generate ics file
    :param summery: summery for ics file
    :param category: summery for ics file
    :param dtstart: datetime object of start time for ics file
    :param dtend: datetime object of end time for ics file
    :param location: location for ics file
    :param description: description for ics file
    :return: ics file path
    """

    path = os.path.join(
        current_app.config['BASE_ICS_FILE_FOLDER'], uuid.uuid4().hex)

    if not os.path.exists(path):
        os.makedirs(path)

    # add calender
    cal = Calendar()
    cal.add('x-wr-calname', summery)
    # create event for calender
    event = Event()
    event.add('summary', summery)
    event.add('dtstart', dtstart.replace(tzinfo=pytz.UTC))
    event.add('dtstamp', dtstart.replace(tzinfo=pytz.UTC))
    if dtend:
        event.add('dtend', dtend.replace(tzinfo=pytz.UTC))
    if description:
        event.add('description', description)
    if location:
        event.add('location', location)
    # adding organizer detail
    organizer = vCalAddress(
        'MAILTO:' + current_app.config['CA_HELPDESK_EMAIL'])
    organizer.params['cn'] = vText(current_app.config[
                                   'DEFAULT_SIGN_OFF_NAME'])
    # organizer.params['role'] = vText('CHAIR')
    # organizer.params['Address'] = vText("S-ancial, Room no: 215")
    event['organizer'] = organizer
    if category:
        event['category'] = category
    # adding the event to calendar
    cal.add_component(event)

    file = os.path.join(path, 'event.ics')
    with open(file, 'wb') as f:
        f.write(cal.to_ical())
        ics_file = file

    return ics_file
