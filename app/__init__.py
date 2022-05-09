import datetime
import logging
import os

#from gevent import monkey
#monkey.patch_all()  # required for socketio
import tweepy

from psycopg2.extensions import register_adapter
from psycopg2.extras import Json, register_default_json
from werkzeug.debug import get_current_traceback
from flask import (
    Flask, render_template, json, jsonify, request, current_app, g)
from flask_cors import CORS
from flask_marshmallow import Marshmallow
from flask_uploads import configure_uploads, UploadSet, IMAGES, DEFAULTS, AUDIO
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_jwt_extended.exceptions import JWTExtendedException
from jwt.exceptions import InvalidTokenError
from flask_restful import Api, abort
from celery import Celery
from celery.utils.log import get_task_logger
from flasgger import Swagger
from apispec import APISpec
from elasticsearch import Elasticsearch
# from elasticsearch.connection import RequestsHttpConnection

from flask_socketio import SocketIO

from app.base.sqlalchemy_hacks import HackSQLAlchemy
from config import (
    ALLOWED_FILES, SOCKET_QUEUE_URL, ELASTICSEARCH_URL, TWITTER_API_KEY,
    TWITTER_API_SECRET_KEY, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET,
    BASE_DIR)
from app.base.constants import VIDEO
from socketapp.base import constants as SOCKETAPP
from app.resources.accounts import constants as ACCT

import queueapp


# Define the WSGI application object
template_folder = os.path.join(BASE_DIR, 'email_html_docs')
flaskapp = Flask(__name__, template_folder=template_folder)
# declare the extensions
db = HackSQLAlchemy()  # check sqlalchemy_hacks file to see more
ma = Marshmallow()
co = CORS()
mig = Migrate()
jwt = JWTManager()
# es = Elasticsearch([ELASTICSEARCH_URL], connection_class=RequestsHttpConnection)
# swagger object creation moved to bottom of file
# #TODO: implement later Create an APISpec
aspec = APISpec(
    title='Corporate Solution',
    version='1.0',
    plugins=(
        'apispec.ext.flask',
        'apispec.ext.marshmallow',
    ),
    info={
        'description': 'A social network connecting investors and companies'
    }
)
sockio = SocketIO(manage_session=True, message_queue=SOCKET_QUEUE_URL)

# authentication of twitter
auth = tweepy.OAuthHandler(
    TWITTER_API_KEY, TWITTER_API_SECRET_KEY)
auth.set_access_token(
    TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
# api connection
tweepy_api = tweepy.API(auth, parser=tweepy.parsers.JSONParser())
# upload sets
# user related
usrprofilephoto = UploadSet('usrprofilephoto', IMAGES)
usrcoverphoto = UploadSet('usrcoverphoto', IMAGES)
# account related
acctprofilephoto = UploadSet('acctprofilephoto', IMAGES)
acctcoverphoto = UploadSet('acctcoverphoto', IMAGES)
# corporate announcements related
corpannctranscript = UploadSet('corpannctranscript', DEFAULTS)
corpanncaudio = UploadSet('corpanncaudio', AUDIO)
corpanncvideo = UploadSet('corpanncvideo', IMAGES)
# file archive related
archivefile = UploadSet(
    'archivefile', DEFAULTS + AUDIO + VIDEO + ALLOWED_FILES)
# project file archive related
projectarchivefile = UploadSet(
    'projectarchivefile', DEFAULTS + AUDIO + VIDEO + ALLOWED_FILES)
# personalised video file related
personalisedvideofile = UploadSet('personalisedvideofile', VIDEO)
# personalised video poster file related
personalisedvideoposterfile = UploadSet(
    'personalisedvideoposterfile', DEFAULTS + VIDEO)
# personalised video demo file relates
personalisedvideodemofile = UploadSet('personalisedvideodemofile', VIDEO)
# post file library related
postfile = UploadSet('postfile', DEFAULTS + AUDIO + VIDEO + ALLOWED_FILES)
# event file library related
eventfile = UploadSet('eventfile', DEFAULTS + ALLOWED_FILES)
# company page file library related
companypagefile = UploadSet('companypagefile', DEFAULTS + ALLOWED_FILES)
# management profile related
manageprofilephoto = UploadSet('manageprofilephoto', IMAGES)
# webcast invite logo related
webcastinvitelogofile = UploadSet('webcastinvitelogofile', IMAGES)
# webcast invite banner related
webcastinvitebannerfile = UploadSet('webcastinvitebannerfile', IMAGES)
# webcast invite video related
webcastvideofile = UploadSet('webcastvideofile', VIDEO)
# webcast invite audio related
webcastaudiofile = UploadSet('webcastaudiofile', AUDIO)
# webinar invite logo related
webinarinvitelogofile = UploadSet('webinarinvitelogofile', IMAGES)
# webinar invite banner related
webinarinvitebannerfile = UploadSet('webinarinvitebannerfile', IMAGES)
# webinar invite video related
webinarvideofile = UploadSet('webinarvideofile', VIDEO)
# webinar invite audio related
webinaraudiofile = UploadSet('webinaraudiofile', AUDIO)
# corporate access event invite logo related
caeventinvitelogofile = UploadSet('caeventinvitelogofile', IMAGES)
# corporate access event invite banner related
caeventinvitebannerfile = UploadSet('caeventinvitebannerfile', IMAGES)
# corporate access event attachment related
caeventattachmentfile = UploadSet(
    'caeventattachmentfile', DEFAULTS + ALLOWED_FILES)
# corporate access open meeting attachment related
caopenmeetingattachmentfile = UploadSet(
    'caopenmeetingattachmentfile', DEFAULTS + ALLOWED_FILES)
# corporate access event invite video related
caeventvideofile = UploadSet('caeventvideofile', VIDEO)
# corporate access event invite audio related
caeventaudiofile = UploadSet('caeventaudiofile', AUDIO)
caeventtranscriptfile = UploadSet('caeventtranscriptfile', DEFAULTS +
                                  ALLOWED_FILES)
# help ticket related
hticketattachment = UploadSet('hticketattachment', DEFAULTS + ALLOWED_FILES)
# help comment related
hcommentattachment = UploadSet('hcommentattachment', DEFAULTS + ALLOWED_FILES)
# newswire post file library related
newswirepostfile = UploadSet('newswirepostfile', IMAGES)
# corporate announcement file related
corporateannouncementfile = UploadSet(
    'corporateannouncementfile', AUDIO + VIDEO + ALLOWED_FILES + IMAGES)
corporateannouncementxmlfile = UploadSet(
    'corporateannouncementxmlfile', ('xml',))
# Market performance file related
accountmarketperformancefile = UploadSet(
    'accountmarketperformancefile', ('xlsx','xls',))
# Distributed list file related
distributionlistfile = UploadSet(
    'distributionlistfile', ('xlsx','xls',))
# research report file related
researchreportfile = UploadSet(
    'researchreportfile', ALLOWED_FILES)
# crm contact profile photo related
crmcontactprofilephoto = UploadSet('crmcontactprofilephoto', IMAGES)
# crm file library related
crmlibraryfile = UploadSet('crmlibraryfile', DEFAULTS + ALLOWED_FILES)
# crm group icon realated
crmgroupicon = UploadSet('crmgroupicon', IMAGES)
# crm distribution list attachment library related
crmdistlistattach = UploadSet('crmdistlistattach', DEFAULTS + ALLOWED_FILES)
# crm distribution list file library related
crmdistlibraryfile = UploadSet('crmdistlibraryfile', IMAGES)
# ir module images
irmodulephotos = UploadSet('irmodulephotos', IMAGES)
# audio transcribe file related
audiotranscribefile = UploadSet(
    'audiotranscribefile', AUDIO)


def create_app(config, create_from='', socket=False, main=True):
    """
    Function that creates the app.
    """
    # global app object, configure it!
    flaskapp.config.from_object(config)

    configure_logger(flaskapp)
    configure_extensions(flaskapp, socket=socket, main=main)
    configure_error_handlers(flaskapp)
    configure_apis(flaskapp)
    if socket:
        configure_socket_namespaces(flaskapp)
    configure_extras(flaskapp)
    return flaskapp


def configure_logger(app, extra_loggers=None):
    """
    Configures the loggers

    :param extra_loggers:
        the names of extra loggers, if passed are used
    """
    if not extra_loggers:
        extra_loggers = []
    if app.config.get('FILE_LOGGING', False):
        # for the command line app, we use file handler
        app_handler = logging.FileHandler(app.config['LOG_FILE'])
    else:
        # for the main and admin apps we use stream handler to rsyslog
        app_handler = logging.StreamHandler()
    log_level = getattr(logging, app.config['LOG_LEVEL'].upper(),
                        logging.NOTSET)
    app_handler.setLevel(log_level)
    formatter = logging.Formatter(
        "CONTAINSAPPLOG: %(asctime)s - %(name)s - %(levelname)s - %(pathname)s"
        " - %(funcName)s - %(lineno)d - %(message)s")
    app_handler.setFormatter(formatter)
    app.logger.addHandler(app_handler)
    # adding a different file for sqlalchemy logging
    if app.config.get('SQLALCHEMY_ECHO', False):
        if app.config.get('FILE_LOGGING', False):
            sql_handler = logging.FileHandler(app.config['LOG_FILE'])
        else:
            sql_handler = logging.StreamHandler()
        sql_logger = logging.getLogger('sqlalchemy')
        sql_log_level = getattr(
            logging, app.config.get(
                'SQLALCHEMY_LOG_LEVEL', app.config['LOG_LEVEL']).upper(),
            logging.NOTSET)
        sql_handler.setLevel(sql_log_level)
        sql_formatter = logging.Formatter(
            "CONTAINSSQLLOG: %(asctime)s - %(name)s - %(levelname)s - "
            "%(pathname)s - %(funcName)s - %(lineno)d - %(message)s")
        sql_handler.setFormatter(sql_formatter)
        sql_logger.addHandler(sql_handler)

    # any extra loggers if any, are simply added to the app handler
    if extra_loggers:
        for log_name in extra_loggers:
            t_logger = logging.getLogger(log_name)
            t_logger.addHandler(app_handler)

    @app.after_request
    def insert_usage_log(response):
        try:
            if (request.method not in ['GET', 'PUT', 'POST', 'DELETE'] or
                    g.current_user['account_type'] == ACCT.ACCT_ADMIN or
                    request.endpoint == 'api.useractivitylogapi'):
                return response
            from app.resources.user_activity_logs.models import UserActivityLog
            req_data = {'response_code': response.status_code,
                        'method': request.method,
                        'end_point': request.endpoint,
                        'args': dict(request.args),
                        'data': {},
                        'login_log_id': g.current_user['login_log_id'],
                        'user_id': g.current_user['row_id'],
                        'account_id': g.current_user['account_id'],
                        'front_end_url': "/".join(
                            request.headers['Referer'].split('/')[3:])}

            if request.method in ['POST', 'PUT']:
                data = request.get_json()
                if not data:
                    data = request.form.to_dict()
                req_data['data'] = data
            log = UserActivityLog(**req_data)
            db.session.add(log)
            db.session.commit()

        except Exception as e:
            pass
        finally:
            return response


def configure_extensions(app, socket=False, main=True):
    """
    Configures the extensions being used
    """
    db.init_app(app)  # flask-sqlalchemy
    ma.init_app(app)  # flask-marshmallow
    co.init_app(app)  # flask-cors
    mig.init_app(app, db)  # flask-migrate
    jwt.init_app(app)  # jwt authentication

    if app.config.get('SWAGGER_ENABLED', app.config.get('DEBUG', False)):
        # enable swagger
        # swg.init_app(app)
        swg1.init_app(app)
        # #TODO: use decorators=[requires_basic_auth] if possible
    if socket:
        # flask-socketio
        if main:
            # socketio app
            sockio.init_app(app, logger=app.logger)
        else:
            # Initialize socketio to emit events through through the message
            # queue
            # Note that since Celery does not use eventlet, we have to be
            # explicit in setting the async mode to not use it.
            sockio.init_app(None, logger=app.logger, async_mode='threading')

    # user related
    configure_uploads(app, (usrprofilephoto))
    configure_uploads(app, (usrcoverphoto))
    # account related
    configure_uploads(app, (acctprofilephoto))
    configure_uploads(app, (acctcoverphoto))
    # corporate announcements related
    configure_uploads(app, (corpannctranscript))
    configure_uploads(app, (corpanncaudio))
    configure_uploads(app, (corpanncvideo))
    # file archive related
    configure_uploads(app, (archivefile))
    # project file archive related
    configure_uploads(app, (projectarchivefile))
    # personalised video file related
    configure_uploads(app, (personalisedvideofile))
    # personalised video poster related
    configure_uploads(app, (personalisedvideoposterfile))
    # personalised video demo file related
    configure_uploads(app, (personalisedvideodemofile))
    # post file library related
    configure_uploads(app, (postfile))
    # event file library related
    configure_uploads(app, (eventfile))
    # company page file library related
    configure_uploads(app, (companypagefile))
    # management profile related
    configure_uploads(app, (manageprofilephoto))
    # webcast invite logo related
    configure_uploads(app, (webcastinvitelogofile))
    # webcast invite banner related
    configure_uploads(app, (webcastinvitebannerfile))
    # webcast invite video related
    configure_uploads(app, (webcastvideofile))
    # webcast invite audio related
    configure_uploads(app, (webcastaudiofile))
    # webinar invite logo related
    configure_uploads(app, (webinarinvitelogofile))
    # webinar invite banner related
    configure_uploads(app, (webinarinvitebannerfile))
    # webinar invite video related
    configure_uploads(app, (webinarvideofile))
    # webinar invite audio related
    configure_uploads(app, (webinaraudiofile))
    # corporate access event invite logo related
    configure_uploads(app, (caeventinvitelogofile))
    # corporate access event invite banner related
    configure_uploads(app, (caeventinvitebannerfile))
    # corporate access event attachment related
    configure_uploads(app, (caeventattachmentfile))
    # corporate access open meeting attachment related
    configure_uploads(app, (caopenmeetingattachmentfile))
    # corporate access event invite video related
    configure_uploads(app, (caeventvideofile))
    # corporate access event invite audio related
    configure_uploads(app, (caeventaudiofile))
    # help ticket related
    configure_uploads(app, (hticketattachment))
    # help comment related
    configure_uploads(app, (hcommentattachment))
    # newswire post file library related
    configure_uploads(app, (newswirepostfile))
    # corporate announcement file related
    configure_uploads(app, (corporateannouncementfile))
    configure_uploads(app, (corporateannouncementxmlfile))
    # account market performance file related
    configure_uploads(app, (accountmarketperformancefile))
    # distribution list field related
    configure_uploads(app, (distributionlistfile))
    # research report file related
    configure_uploads(app, (researchreportfile))
    # crm contact profile photo
    configure_uploads(app, (crmcontactprofilephoto))
    # crm file library
    configure_uploads(app, (crmlibraryfile))
    # crm group icon
    configure_uploads(app, (crmgroupicon))
    configure_uploads(app, (caeventtranscriptfile))
    configure_uploads(app, (caeventaudiofile))
    configure_uploads(app, (crmdistlistattach))
    configure_uploads(app, (crmdistlibraryfile))
    # ir module photo
    configure_uploads(app, (irmodulephotos))
    # audio transcribe file related
    configure_uploads(app, (audiotranscribefile))

    return


def configure_error_handlers(app):
    """
    Configures the error handlers used
    """

    @app.errorhandler(404)
    def error_404(error):
        errors_50x(error, dont_send=True)
        if 'api/v1.0' in request.url:
            # was supposed to be an api call
            return jsonify({'message': 'Route not found'}), 404
        return '{}', 404

    @app.errorhandler(500)
    def error_500(error):
        errors_50x(error)
        return '{}', 500

    @app.errorhandler(501)
    def error_501(error):
        errors_50x(error)
        return '{}', 501

    @app.errorhandler(502)
    def error_502(error):
        errors_50x(error)
        return '{}', 502

    @app.errorhandler(503)
    def error_503(error):
        errors_50x(error)
        return '{}', 503


def configure_apis(app):
    """
    Configures the apis exposed
    """
    # add the frontend email test api only if debug mode
    if app.config.get('SWAGGER_ENABLED', app.config.get('DEBUG', False)):
        from app.api import fetest_api_bp as fetest_api_module
        app.register_blueprint(fetest_api_module)

    # social network + user apis
    from app.api import api_bp as api_module
    app.register_blueprint(api_module)

    # toolkit apis
    from app.toolkit_resources.api import toolkit_api_bp as toolkit_api_module
    app.register_blueprint(toolkit_api_module)

    # webcast apis
    from app.webcast_resources.api import webcast_api_bp as webcast_api_module
    app.register_blueprint(webcast_api_module)

    # webinar apis
    from app.webinar_resources.api import webinar_api_bp as webinar_api_module
    app.register_blueprint(webinar_api_module)

    # corporate_access apis
    from app.corporate_access_resources.api import corporate_access_api_bp as\
        corporate_access_api_module
    app.register_blueprint(corporate_access_api_module)

    # helpdesk_resources apis
    from app.helpdesk_resources.api import helpdesk_api_bp as\
        helpdesk_api_module
    app.register_blueprint(helpdesk_api_module)

    # newswire apis
    from app.newswire_resources.api import newswire_api_bp as\
        newswire_api_module
    app.register_blueprint(newswire_api_module)

    # disclosure_enhancement_resource apis
    from app.disclosure_enhancement_resources.api import (
        disclosure_enhancement_api_bp)
    app.register_blueprint(disclosure_enhancement_api_bp)

    # crm_resource apis
    from app.crm_resources.api import crm_api_bp
    app.register_blueprint(crm_api_bp)

    # semi documentation
    from app.semidocument_resources.api import semi_documentation_api_bp
    app.register_blueprint(semi_documentation_api_bp)

    # ecg framework
    from app.esg_framework_resources.api import esg_api_bp
    app.register_blueprint(esg_api_bp)

def configure_socket_namespaces(app):
    """
    Configures the socket namespaces exposed
    """
    # /socket.io/chats
    #from socketapp.chats.events import ChatsNamespace
    #sockio.on_namespace(ChatsNamespace(SOCKETAPP.NS_CHAT))

    # /socket.io/notifications
    from socketapp.notifications.events import NotificationsNamespace
    sockio.on_namespace(NotificationsNamespace(SOCKETAPP.NS_NOTIFICATION))
    sockio.on_namespace(NotificationsNamespace(SOCKETAPP.NS_DESIGNLAB_NOTIFICATION))

    # /socket.io/feeds
    #from socketapp.feeds.events import FeedsNamespace
    #sockio.on_namespace(FeedsNamespace(SOCKETAPP.NS_FEED))


def configure_extras(app):
    """
    Configure any extra stuff
    """

    # some postgresql related json conversion helpers
    # convert datetime objects to isoformat while storing in json(b)
    class DateJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            return json.JSONEncoder.default(self, obj)

    class DateJson(Json):
        def dumps(self, obj):
            return json.dumps(obj, cls=DateJSONEncoder)

    # register adapter to convert json without errors, such as:
    # #TODO: psycopg2.ProgrammingError: can't adapt type 'dict'
    register_adapter(dict, DateJson)

    # convert isoformat date string back to datetime object while loading
    # that is in library_hacks, for some reason register_default_json
    # is not working
    # register_default_json(globally=True, loads=dateloads)

    @jwt.expired_token_loader
    def jwt_expired_token_callback():
        """
        Changing to change 'msg' key to 'message'
        """
        return jsonify({'message': 'Token has expired'}), 401

    @jwt.invalid_token_loader
    def jwt_invalid_token_callback(error_string):
        """
        Changing to change 'msg' key to 'message'

        :param error_string: String indicating why the token is invalid
        """
        return jsonify({'message': error_string}), 422

    @jwt.unauthorized_loader
    def jwt_unauthorized_callback(error_string):
        """
        Changing to change 'msg' key to 'message'

        :param error_string: String indicating why this request is unauthorized
        """
        return jsonify({'message': error_string}), 401

    @jwt.needs_fresh_token_loader
    def jwt_needs_fresh_token_callback():
        """
        Changing to change 'msg' key to 'message'
        """
        return jsonify({'message': 'Fresh token required'}), 401

    @jwt.revoked_token_loader
    def jwt_revoked_token_callback():
        """
        Changing to change 'msg' key to 'message'
        """
        return jsonify({'message': 'Token has been revoked'}), 401

    @jwt.user_loader_error_loader
    def jwt_user_loader_error_callback(identity):
        """
        Changing to change 'msg' key to 'message'
        """
        return jsonify({'message': "Error loading the user {}".format(
            identity)}), 401

    if app.config.get('SWAGGER_ENABLED', app.config.get('DEBUG', False)):
        @app.route('/sockettest')
        def sockettest():
            return render_template('index.html', async_mode=sockio.async_mode)

    return


def errors_50x(error, dont_send=False):
    """
    Logs the error, and sends out error email.
    """
    uid_name = '-1_guest'
    if 'current_user' in g and g.current_user:
        uid_name = str(g.current_user['row_id']) + '_' +\
            str(g.current_user['profile']['first_name'])

    e = 'User= ' + uid_name + ' accessed ' + request.url +\
        ' method= ' + request.method + ' with ip=' +\
        request.environ.get('REMOTE_ADDR', request.remote_addr)

    e += '\nargs = ' + str(request.args) + '\npost = ' + str(request.form) +\
        '\njson = ' + str(request.get_json())

    current_app.logger.exception(e)
    current_app.logger.exception(error)

    if dont_send:  # don't send the error
        return

    track = get_current_traceback(skip=1, show_hidden_frames=True,
                                  ignore_system_exceptions=False)
    e += '\n' + track.plaintext
    queueapp.tasks.send_email_task.delay(email_type='error', e=e)


def make_celery(app):
    """
    Function to generate the celery global app.
    ***Remember for immediate calling use .s().apply() instead of direct
    .apply() as kwargs errors.
    """
    if 'CELERY_BROKER_URL' not in app.config:
        app.config.from_object('config')
    celery = Celery(app.import_name,
                    # backend=app.config['CELERY_RESULT_BACKEND'],
                    broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True
        max_retries = 20

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

        def signature(self, args=None, *starargs, **starkwargs):
            """Create signature. Overriding base to include log_uid

            Inserts the log uid to first dict of *starargs.
            :param args:
                the arguments of the task.
            :param *starargs:
                the ** args of the task, i.e keyword arguments
            :param **starkwargs:
                celery specific arguments

            Returns:
                :class:`~celery.signature`:  object for
                    this task, wrapping arguments and execution options
                    for a single task invocation.
            """
            log_uid = -1
            try:
                if 'current_user' in g and g.current_user:
                    log_uid = g.current_user['row_id']
            except Exception:
                log_uid = -1
            starkwargs['log_uid'] = log_uid
            mod_starargs = starargs + ()
            if mod_starargs:
                if 'log_uid' not in mod_starargs[0]:
                    first_starstarargs = mod_starargs[0].copy()
                    first_starstarargs['log_uid'] = log_uid
                    starargs = (first_starstarargs,) + mod_starargs[1:]
                else:
                    # during retries?
                    pass
            else:
                starargs = ({'log_uid': log_uid},)
            return super(ContextTask, self).\
                signature(args, *starargs, **starkwargs)
        subtask = signature

        def apply(self, args=None, kwargs=None, link=None, link_error=None,
                  **options):
            """
            :param args: positional arguments passed on to the task.
            :param kwargs: keyword arguments passed on to the task.
            """
            log_uid = -1
            try:
                if 'current_user' in g and g.current_user:
                    log_uid = g.current_user['row_id']
            except Exception:
                log_uid = -1
            # during chaining log_uid will already be there, taken from delay
            if 'log_uid' not in kwargs:
                kwargs['log_uid'] = log_uid
            return super(ContextTask, self).\
                apply(args=args, kwargs=kwargs, link=link,
                      link_error=link_error, **options)

        def apply_async(self, args=None, kwargs=None, task_id=None,
                        producer=None, link=None, link_error=None, **options):
            """
            :param args: positional arguments passed on to the task.
            :param kwargs: keyword arguments passed on to the task.
            """
            log_uid = -1
            try:
                if 'current_user' in g and g.current_user:
                    log_uid = g.current_user['row_id']
            except Exception:
                log_uid = -1
            if 'log_uid' not in kwargs:
                kwargs['log_uid'] = log_uid

            return super(ContextTask, self).\
                apply_async(args=args, kwargs=kwargs, task_id=task_id,
                            producer=producer, link=link,
                            link_error=link_error, **options)

        def after_return(self, status, retval, task_id, args, kwargs, einfo):
            """
            Overriding the parent to handle max retries exceeded exception.
            """
            if self.max_retries == self.request.retries:
                # If max retries is equal to task retries log it
                logger = get_task_logger('queueapp.tasks')
                logger.exception('Error in %s' % str(task_id))
                if args:
                    e_args = 'Args = ' + json.dumps(args)
                if kwargs:
                    k_args = ' KwArgs = ' + json.dumps(kwargs)
                e = e_args + k_args
                e += ' task_id= ' + str(task_id)
                e += ' status= ' + str(status)
                e += ' retval= ' + str(retval)
                e += ' task name= ' + str(self.name)
                e += ' error info= ' + str(einfo)
                logger.exception(e)
                with app.test_request_context():
                    queueapp.tasks.send_error_email_from_tasks(e)
            super(ContextTask, self).after_return(status, retval, task_id,
                                                  args, kwargs, einfo)

    celery.Task = ContextTask
    return celery


def c_abort(http_status_code, message='', errors=None, **kwargs):
    """
    Custom abort function to make easy messages using CustomBaseApi
    ** automatically adds the message for 400 'No input data provided'

    :param message:
        a custom string message
    :param errors:
        a dictionary of errors, generally form errors, i.e in the format of
        {<column key>: ['error message1', 'error message2'], ... }
    """
    kwargs['is_custom'] = True
    if message:
        kwargs['message'] = message
    else:
        if http_status_code == 400:
            kwargs['message'] = 'No input data provided'
    if errors:
        kwargs['errors'] = errors
    abort(http_status_code, **kwargs)


class CustomBaseApi(Api):
    """
    Overloading the flask-restful Api for custom error handling
    """

    def handle_error(self, e):
        """
        Custom error handler
        """
        code = getattr(e, 'code', 500)
        if isinstance(e, JWTExtendedException) or isinstance(
                e, InvalidTokenError):
            return super(CustomBaseApi, self).handle_error(e)
        else:
            # handle custom aborts
            if (hasattr(e, 'data') and e.data and 'is_custom' in e.data and
                    e.data['is_custom']):
                e_response = {}
                if 'message' in e.data:
                    e_response['message'] = e.data['message']
                if 'errors' in e.data:
                    e_response['errors'] = e.data['errors']
                return self.make_response(e_response, code)
            # handle 500s
            if code >= 500:
                errors_50x(e)
                return self.make_response({
                    'message': 'Unexpected error occurred, we are already'
                    ' working on a fix!'}, 500)
            # handle unknown aborts
            return super(CustomBaseApi, self).handle_error(e)

from app.auth.decorators import requires_basic_auth

swg = Swagger(decorators=[requires_basic_auth], template={
    'swagger': '2.0',
    'info': {
        'title': 'Corporate Solution',
        'version': '1.0',
        'description':
            'A social network connecting investors and companies',
    },
    'consumes': [
        'application/json',  # 'form'
    ],
    'produces': [
        'application/json',
    ],
})

def rule_filter(rule):
    if '/design-lab-projects' in rule.rule:
        return True
    return False

SWAGGER_CONFIG = {
        "headers": [
        ],
        "specs": [
            {
                "endpoint": 'apispec_2',
                "route": '/apispec_2.json',
                "rule_filter": rule_filter,
                "model_filter": lambda tag: True,  # all in
            }
        ],
        "static_url_path": "/flasgger_static",
        # "static_folder": "static",
        "swagger_ui": True,
        "specs_route": "/designlab_api/"
    }

swg1 = Swagger(template={
    'swagger': '2.0',
    'info': {
        'title': 'Corporate Solution',
        'version': '1.0',
        'description':
            'A social network connecting investors and companies',
    },
    'consumes': [
        'application/json',  # 'form'
    ],
    'produces': [
        'application/json',
    ],
}, config=SWAGGER_CONFIG)

from queueapp.tasks import send_email_task
# ^ required for activating queueapp
