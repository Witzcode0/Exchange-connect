"""
Add any common utility functions/classes here.
Note utility here means unrelated directly with the app, but helpful
in doing smaller things like, sending an email, or calculating average!
"""

import os
import errno
import smtplib
import mimetypes
import pytz
import dns.resolver
import requests
import base64

from io import IOBase
from email import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formataddr
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

from flask import current_app
from boto3.session import Session
from itsdangerous import URLSafeSerializer, URLSafeTimedSerializer
from preview_generator.manager import PreviewManager


def do_nothing(*args, **kwargs):
    """
    Just return back the first arg passed or None, without doing anything.
    """
    result = None
    if args:
        result = args[0]
    return result


def get_aws_session(res_name='', client_name='', access_key='',
                    access_secret='', region_name=None):
    """
    Gets the signed session resource.

    :param res_name:
        which aws resource to return, right now only S3 is supported
    :param client_name:
        which aws client to return, right now only SES is supported
    :param access_key:
        provide an access key, if passed, is used
    :param access_secret:
        provide an access secret, if passed, is used
    :param region_name:
        provide a region name, if passed, is used

    :returns the resource, or raises exception
    """

    if not res_name and not client_name:
        raise Exception('Both res_name and client_name are empty')

    access_key = access_key or current_app.config['S3_ACCESS_KEY']
    access_secret = access_secret or current_app.config['S3_ACCESS_SECRET']
    region_name = region_name or current_app.config['AWS_REGION'] or None
    res_client = None

    try:
        session = Session(
            aws_access_key_id=access_key, aws_secret_access_key=access_secret,
            region_name=region_name)
        if res_name:
            res_client = session.resource(res_name)
        elif client_name:
            res_client = session.client(client_name)
    except Exception as e:
        current_app.logger.exception(e)
        raise e

    return res_client


def upload_to_s3(source_file, destination, bucket_name='', acl='private',
                 metadata=None, access_key='', access_secret=''):
    """
    Uploads to a file to s3.

    :param source_file:
        the source file absolute path
    :param destination:
        the destination s3 path with filename
    :param bucket_name:
        the bucket name
    :param acl:
        access control permission
    :param metadata:
        any extra metadata
    :param access_key:
        provide an access key, if passed, is used
    :param access_secret:
        provide an access secret, if passed, is used

    :returns True or False, or raises exception
    """
    status = False
    bucket_name = bucket_name or current_app.config['S3_BUCKET']
    try:
        s3_res = get_aws_session(res_name='s3', access_key=access_key,
                                 access_secret=access_secret)
        bucket = s3_res.Bucket(bucket_name)
        extra_args = {'ACL': acl}
        if metadata:
            extra_args['Metadata'] = metadata
        kwargs = {}
        bucket.upload_file(
            source_file, destination, ExtraArgs=extra_args, **kwargs)
        status = True
    except Exception as e:
        current_app.logger.exception(e)
        raise e
    return status


def get_s3_download_link(key, bucket_name='', expires_in=3600, destination='',
                         access_key='', access_secret='', region_name=None):
    """
    Generates a signed s3 download link.

    :param key:
        the target key (file to download)
    :param bucket_name:
        the bucket name
    :param expires_in:
        the time in which the url expires
    :param destination:
        the destination filename, if provided, uses it, else defaults to
        whatever S3 provides.
    :param access_key:
        provide an access key, if passed, is used
    :param access_secret:
        provide an access secret, if passed, is used
    :param region_name:
        provide a region name, if passed, is used

    :returns url or empty url, or raised exception
    """
    url = ''
    bucket_name = bucket_name or current_app.config['S3_BUCKET']
    try:
        # Get the service client.
        s3_res = get_aws_session(res_name='s3', access_key=access_key,
                                 access_secret=access_secret,
                                 region_name=region_name)
        client = s3_res.meta.client
        url = client.generate_presigned_url(
            ClientMethod='get_object', Params={
                'Bucket': bucket_name, 'Key': key}, ExpiresIn=expires_in)
    except Exception as e:
        raise e
    return url


def get_s3_file_size(key, bucket_name='', access_key='', access_secret='',
                     region_name=None):
    """
    Get file size from s3
    :param key:
        the target key (file to download)
    :param bucket_name:
        the bucket name
    :param access_key:
        provide an access key, if passed, is used
    :param access_secret:
        provide an access secret, if passed, is used
    :param region_name:
    :return:
    """
    file_size = 0
    bucket_name = bucket_name or current_app.config['S3_BUCKET']
    try:
        # Get the service client.
        s3_res = get_aws_session(res_name='s3', access_key=access_key,
                                 access_secret=access_secret,
                                 region_name=region_name)
        client = s3_res.meta.client
        response = client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=key,)
        for obj in response.get('Contents', []):
            if obj['Key'] == key:
                file_size = obj['Size']
    except Exception as e:
        raise e

    return file_size


def copy_s3_to_s3(key, aws_src_path_key, f_name,
                  bucket_name='', destination='', access_key='',
                  access_secret='', region_name=None):
    """
    copy file from s3 to s3

    :param key:
        the target key (file to copy)
    :param bucket_name:
        the bucket name
    :param destination:
        the destination filename, if provided, uses it, else defaults to
        whatever S3 provides.
    :param access_key:
        provide an access key, if passed, is used
    :param access_secret:
        provide an access secret, if passed, is used
    :param region_name:
        provide a region name, if passed, is used

    :returns status True or False, or raised exception
    """
    status = False
    bucket_name = bucket_name or current_app.config['S3_BUCKET']
    region_name = region_name or current_app.config['AWS_REGION'] or None
    try:
        # Get the service client
        s3_res = get_aws_session(res_name='s3', access_key=access_key,
                                 access_secret=access_secret,
                                 region_name=region_name)
        copy_source = {
            'Bucket': bucket_name,
            'Key': aws_src_path_key
        }
        bucket = s3_res.Bucket(bucket_name)
        bucket.copy(copy_source, key)
        status = True
    except Exception as e:
        raise e
    return status

def delete_folder_from_s3(full_folder, bucket_name='', access_key='', access_secret='',
                   extra_args=None, quiet=False):
    """
    Deletes an s3 file.

    :param keys:
        the s3 file keys as a list
    :param bucket_name:
        the bucket name from which to delete.
    :param access_key:
        provide an access key, if passed, is used
    :param access_secret:
        provide an access secret, if passed, is used

    :returns True or False, or raises exception
    """
    status = False
    bucket_name = bucket_name or current_app.config['S3_BUCKET']
    try:
        s3_res = get_aws_session(res_name='s3', access_key=access_key,
                                 access_secret=access_secret)
        bucket = s3_res.Bucket(bucket_name)
        counter = 0
        # bucket.objects.filter(Prefix="audiotranscribefile/28/").delete()
        for obj in bucket.objects.filter(Prefix=full_folder):
            print(obj.key)
            try:
                obj.delete()
                counter = counter + 1
            except:
                print("error occurred while deleting")
    except Exception as e:
        current_app.logger.exception(e)
        raise e

    return status


def delete_from_s3(keys, bucket_name='', access_key='', access_secret='',
                   extra_args=None, quiet=False):
    """
    Deletes an s3 file.

    :param keys:
        the s3 file keys as a list
    :param bucket_name:
        the bucket name from which to delete.
    :param access_key:
        provide an access key, if passed, is used
    :param access_secret:
        provide an access secret, if passed, is used

    :returns True or False, or raises exception
    """
    status = False
    bucket_name = bucket_name or current_app.config['S3_BUCKET']
    try:
        s3_res = get_aws_session(res_name='s3', access_key=access_key,
                                 access_secret=access_secret)
        bucket = s3_res.Bucket(bucket_name)
        delete_dict = {}
        delete_dict['Objects'] = [{'Key': k} for k in keys]
        if quiet:
            delete_dict['Quiet'] = True
        kwargs = {}
        bucket.delete_objects(Delete=delete_dict, **kwargs)
        status = True
    except Exception as e:
        current_app.logger.exception(e)
        raise e
    return status


def get_s3_file(
        source, destination, bucket=None, access_key='', access_secret=''):
    """
    Gets an S3 file to destination.

    :param source:
        the s3 file path
    :param destination:
        either a file object, pathname, or None
    :param bucket:
        the bucket name
    :param access_key:
        provide an access key, if passed, is used
    :param access_secret:
        provide an access secret, if passed, is used
    :returns a string if destination is None, else populates the destination
        object

    """
    bucket_name = bucket or current_app.config['S3_BUCKET']
    s3_res = get_aws_session(
        res_name='s3', access_key=access_key, access_secret=access_secret)
    try:
        k = s3_res.Bucket(bucket_name)
        if isinstance(destination, IOBase):
            k.download_file(source, destination)
        elif isinstance(destination, str):
            dest_dir = os.path.dirname(destination)
            if not os.path.exists(dest_dir):
                try:
                    os.makedirs(dest_dir)
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        # if there was some other OSError then we raise it
                        # otherwise if directory(s) already exists we continue
                        raise
            k.download_file(source, destination)
        else:
            k.download_file(source, destination)
    except Exception as e:
        current_app.logger.exception(e)


def verify_ses_sender_identity(
        identity, access_key='', access_secret='', region_name=None,
        custom_template_name=''):
    """
    Adds a verification request in SES for 'identity', incase the identity is
    an email address, the SES email verification email is sent, incase the
    identity is a domain then the domain verification is returned

    :param identity:
        the email address to verify
    :param access_key:
        provide an access key, if passed, is used
    :param access_secret:
        provide an access secret, if passed, is used
    :param region_name:
        provide a region name, if passed, is used
    :param custom_template_name:
        a custom template name, if passed, is used

    :returns sent status and response or empty response, or raises exception
    """

    region_name = region_name or current_app.config['AWS_SES_REGION'] or\
        current_app.config['AWS_REGION'] or None

    sent = False
    response = {}
    try:
        # Get the service client.
        client = get_aws_session(client_name='ses', access_key=access_key,
                                 access_secret=access_secret,
                                 region_name=region_name)
        if '@' in identity:
            if custom_template_name:
                response = client.send_custom_verification_email(
                    EmailAddress=identity,
                    TemplateName=custom_template_name)
            else:
                response = client.verify_email_identity(EmailAddress=identity)
        else:
            response = client.verify_domain_identity(
                Domain=identity)
        if (response and 'ResponseMetadata' in response and
                'HTTPStatusCode' in response['ResponseMetadata'] and
                response['ResponseMetadata']['HTTPStatusCode'] == 200):
            sent = True
    except Exception as e:
        raise e
    return sent, response


def check_ses_identity_verification_status(
        identity, access_key='', access_secret='', region_name=None):
    """
    Checks the ses email identity verification status.

    :param identity:
        the identity whose status is to be checked
    :param access_key:
        provide an access key, if passed, is used
    :param access_secret:
        provide an access secret, if passed, is used
    :param region_name:
        provide a region name, if passed, is used

    :returns verified status and response or empty response, or
        raises exception
    """

    region_name = region_name or current_app.config['AWS_SES_REGION'] or\
        current_app.config['AWS_REGION'] or None

    verified = False
    response = {}
    try:
        # Get the service client.
        client = get_aws_session(client_name='ses', access_key=access_key,
                                 access_secret=access_secret,
                                 region_name=region_name)
        response = client.get_identity_verification_attributes(
            Identities=[identity])
        if (response and 'VerificationAttributes' in response and
                identity in response['VerificationAttributes'] and
                response['VerificationAttributes'][identity][
                    'VerificationStatus'] == 'Success'):
            verified = True
    except Exception as e:
        raise e
    return verified, response


def remove_ses_identity(
        identity, access_key='', access_secret='', region_name=None):
    """
    Removes the sender identity from SES.

    :param identity:
        the identity whose status is to be checked
    :param access_key:
        provide an access key, if passed, is used
    :param access_secret:
        provide an access secret, if passed, is used
    :param region_name:
        provide a region name, if passed, is used

    :returns verified status and response or empty response, or
        raises exception
    """

    region_name = region_name or current_app.config['AWS_SES_REGION'] or\
        current_app.config['AWS_REGION'] or None

    removed = False
    response = {}
    try:
        # Get the service client.
        client = get_aws_session(client_name='ses', access_key=access_key,
                                 access_secret=access_secret,
                                 region_name=region_name)
        response = client.delete_identity(Identity=identity)
        if (response and 'ResponseMetadata' in response and
                'RequestId' in response['ResponseMetadata'] and
                response['ResponseMetadata']['RequestId']):
            removed = True
    except Exception as e:
        raise e
    return removed, response


def check_domain_records(domain, record=''):
    """
    Can check for DNS records
    """

    result = False
    response = ''

    try:
        answers = dns.resolver.query(domain, 'TXT')
        for rdata in answers:
            if ('v=spf1' in str(rdata) and
                    'include:amazonses.com' in str(rdata)):
                result = True
                response = str(rdata)
                break
    except dns.resolver.NoAnswer as e:
        current_app.logger.exception(e)
    except dns.exception.DNSException as e:
        current_app.logger.exception(e)
    except Exception as e:
        current_app.logger.exception(e)

    return result, response


def delete_fs_file(path, fail_enoent=False):
    """
    Removes a file from filesystem. By default fails silently for non-existant
    files
    """
    try:
        os.remove(path)
    except OSError as e:
        if e.errno != errno.ENOENT:
            current_app.logger.exception(e.message)
            return False
        elif fail_enoent:
            current_app.logger.exception(e.message)
            return False
    return True


def send_email(username, password, smtphost, from_name='', from_email='',
               reply_to='--', to_addresses=None, cc_addresses=None,
               bcc_addresses=None, subject='', body='', html='', keywords='',
               attachment='', port=465, is_ssl=True, ics_file=None):
    """
    Sends an email.

    :param username:
        smtp username
    :param password:
        smtp password
    :param smtphost:
        smtp host
    :param from_name:
        the sender name
    :param from_email:
        the sender email
    :param reply_to:
        the reply_to address, if it is '--' then reply to is not filled, if it
        is empty then copies the from_email
    :param to_addresses:
        the to addresses as a list of addresses
    :param cc_addresses:
        the to cc_addresses as a list of addresses
    :param subject:
        the subject
    :param body:
        the text body
    :param html
        the html body
    :param attachment:
        the attachment absolute path
    """
    if to_addresses is None:
        to_addresses = []
    if cc_addresses is None:
        cc_addresses = []
    if bcc_addresses is None:
        bcc_addresses = []
    if not from_email:
        current_app.logger.exception('From email empty')
        return
    to_addresses = list(filter(None, to_addresses))
    if not to_addresses:
        current_app.logger.exception('To address empty')
        return
    if not any([html, attachment, ics_file]):
        message = MIMEText(body, 'plain', 'utf-8')
    else:
        message = MIMEMultipart('alternative')
        part1 = MIMEText(body, 'plain', 'utf-8')
        part2 = ''
        if html:
            part2 = MIMEText(html, 'html', 'utf-8')
        # Attach parts into message container.
        # According to RFC 2046, the last part of a multipart message, in this
        # case the HTML message, is best and preferred.
        message.attach(part1)
        if part2:
            message.attach(part2)

        # if multiple attachment files
        if not isinstance(attachment, list):
            attachment = [attachment]
        for attach in attachment + [ics_file]:
            if not attach:
                continue
            fname = os.path.basename(attach)
            ctype, encoding = mimetypes.guess_type(attach)
            if ctype is None or encoding is not None:
                # No guess could be made, or the file is encoded
                # (compressed),
                # so use a generic bag-of-bits type.
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)
            fp = open(attach, 'rb')
            atch_msg = MIMEBase(maintype, subtype)
            atch_msg.set_payload(fp.read())
            fp.close()
            # Encode the payload using Base64
            encoders.encode_base64(atch_msg)
            # Set the filename parameter
            atch_msg.add_header('Content-Disposition', 'attachment',
                                filename=fname)
            message.attach(atch_msg)

    message['Subject'] = subject
    message['From'] = formataddr((from_name, from_email))
    message['To'] = ", ".join(to_addresses)
    message['Cc'] = ", ".join(cc_addresses)
    if current_app.config['CONFIGURATION_SET_ENABLE']:
        message['X-SES-CONFIGURATION-SET'] = current_app.config['CONFIGURATION_SET']
    message['X-SES-CONFIGURATION-SET'] = 'csdailymail_test'
    message['keywords'] = keywords

    if reply_to != '--':
        message['Reply-To'] = reply_to if reply_to else from_email

    if is_ssl:
        smtp = smtplib.SMTP_SSL(smtphost, port)
    else:
        smtp = smtplib.SMTP(smtphost, port)

    try:
        smtp.login(username, password)
        smtp.sendmail(from_email, to_addresses + cc_addresses + bcc_addresses,
                      message.as_string())
    except Exception as e:
        raise e
    finally:
        smtp.quit()


def create_local_directories(path):
    """
    Creates local directories.

    Raises general exception if there was an error.

    :param path:
        the path without basename
    """
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                # if there was some other OSError then we raise it
                # otherwise if directory(s) already exists we continue
                raise


def get_serializer(secret_key=None, timed=True):
    """
    Returns an itsdangerous serializer

    :param secret_key:
        the secret key for the serializer, used if passed
    :param timed:
        boolean, indicating whether to create a timed serializer
    """
    app = current_app._get_current_object()
    if secret_key is None:
        secret_key = app.secret_key
    if timed:
        serializer = URLSafeTimedSerializer(secret_key)
    else:
        serializer = URLSafeSerializer(secret_key)
    return serializer


def get_payload_from_value(value, serializer=None):
    """
    Function to generate an itsdangerous payload from a value.

    :param value:
        the value to encode
    :param serializer:
        a specific serializer, if passed is used
    """
    s = serializer or get_serializer()
    return s.dumps(str(value))


def get_value_from_payload(payload, max_age=172800, raise_ex=False,
                           force=False):
    """
    Function that decrypts an itsdangerous payload.

    :param payload:
        the payload to decrypt.
    :param max_age:
        the maximum age of the payload allowed for timed signatures in seconds,
        default max_age is 172800 seconds (2 days)
    :param force:
        whether the value should be decoded regardless of expiry, defaults to
        False.
    :return value:
        decrpyted payload value.
    """
    s = get_serializer()
    value = None
    if force:
        value = s.load_payload(payload)
    else:
        value = s.loads(payload, max_age=max_age)
    return value


def time_converter(dt_obj, to=None, frm=None):
    """
    Converts naive datetime between timezones.
    """
    dt_obj = dt_obj.replace(tzinfo=None)
    if not frm:
        frm = current_app.config['SYSTEM_TIMEZONE']
    if not to:
        to = current_app.config['USER_DEFAULT_TIMEZONE']
    ret = dt_obj

    try:
        ret = pytz.timezone(frm).localize(dt_obj).\
            astimezone(pytz.timezone(to))
    except Exception as e:
        current_app.logger.exception(e)
    return ret


def generate_thumbnail(filename, source_path, page=None, width=None,
                       height=None):
    """
    Convert normal file into thumbnail
    :param filename:
        filename is original file which is converting into thumbnail
    :param source_path:
        converted thumbnail source path
    :param page:
        how many pages converted into thumbnail, this is mainly used in pdf
        file, otherwise by default its value is 0
    :param width:
        width of thumbnail in pixel
    :param height:
        height of thumbnail in pixel
    """
    page = page or current_app.config['THUMBNAIL_PAGE']
    width = width or current_app.config['THUMBNAIL_PIXEL'][0]
    height = height or current_app.config['THUMBNAIL_PIXEL'][1]

    manager = PreviewManager(source_path, create_folder=True)
    thumbnail_file_path = manager.get_jpeg_preview(
        filename, page=page, width=width, height=height)

    return thumbnail_file_path


def calling_bigmarker_apis(bigmarker_url='', sub_url='', api_key='',
                           content_type='', json_data=None, method='get'):
    """
    call bigmarker third party api.
    create conference by adding conference_id and urls to db.
    update conference if exists by check with conference_id.
    generate admin url for admin access.

    :param bigmarker_url: 'https://www.bigmarker.com/api/v1/'
    :param sub_url: sub_url for registration, delete or update
    :param api_key: api_key for header
    :param content_type: content_type for header
    :param method: request method
    :param json_data: json object
    :return: response from bigmarker
    """
    headers = {}
    url = bigmarker_url or current_app.config['BIGMARKER_REQUEST_URL']
    headers['content-type'] = content_type or 'application/json'
    headers['API-KEY'] = api_key or current_app.config['BIGMARKER_API_KEY']

    bigmarker_api_url = url + sub_url
    try:
        if method == 'post':
            response = requests.post(
                bigmarker_api_url, json=json_data, headers=headers)
        elif method == 'put':
            response = requests.put(
                bigmarker_api_url, json=json_data, headers=headers)
        elif method == 'delete':
            response = requests.delete(
                bigmarker_api_url, json=json_data, headers=headers)
        elif method == 'get':
            response = requests.get(
                bigmarker_api_url, headers=headers)
    except Exception as e:
        raise e

    return response


def push_notification(data):
    """
    Calling firebase push notification api
    :param data: json data for sending push notification
    :return:
    """

    headers = {}
    url = current_app.config['FIREBASE_URL']
    headers['content-type'] = 'application/json'
    headers['Authorization'] = current_app.config['FIREBASE_KEY']

    try:
        response = requests.post(
                url, json=data, headers=headers)
    except Exception as e:
        raise e

    return response


def create_encryption_decryption_key():
    """
    its create key for encryption and decryption
    :return: key
    """
    smtp_password_key = b'vndbvghdvsznxbs'

    salt = b'fdlmfkfuis_'
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(smtp_password_key))

    return key


def custom_sorted(collection, key=None, unorderable_to_last=True):
    # if called with unorderable_to_last returns sorted list
    # with unorderable at last
    # if unorderable_to_last is set False will behave
    # same that of inbuilt sorted function
    if not unorderable_to_last:
        return sorted(collection, key=key)
    orderable = []
    unorderable = []
    if not collection:
        return []
    for each in collection:
        if key(each) != None:
            orderable.append(each)
        else:
            unorderable.append(each)
    result = sorted(orderable, key=key)
    result.extend(unorderable)
    return result


def get_dict_value(data, keys, default=None):
    """
    this function will return value in nested dicts
    helpful in cases where any key is missing,
    instead of raising error it will return default value.
    usage: x = my_dict['a']['b']['c'] will raise keyerror if a, b or c
     is not present if you simply want None in that case use this function
    e.g x = get_val_nested_dict()
    :param data: dictionary
    :param keys: iterable of keys
    :return:
    """
    value = None
    for key in keys:
        try:
            value = data[key]
            data = value
        except Exception:
            return default
    return value