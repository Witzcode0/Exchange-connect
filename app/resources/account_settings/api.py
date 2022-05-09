"""
API endpoints for "account settings" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from flasgger.utils import swag_from

from app import db, c_abort
from app.base import constants as APP
from app.base.api import AuthResource
from app.resources.account_settings.models import AccountSettings
from app.resources.account_settings.schemas import AccountSettingsSchema
from app.resources.account_settings.helpers import (
    verify_email, remove_verified_identity)


class AccountSettingsAPI(AuthResource):
    """
    Put and Get API for account settings
    """

    @swag_from('swagger_docs/account_settings_put.yml')
    def put(self):
        """
        Update account settings
        """
        extra_message = ''
        account_settings_schema = AccountSettingsSchema()

        # first find model
        model = None
        old_event_sender_email = ''
        try:
            model = AccountSettings.query.options(joinedload(
                AccountSettings.account)).filter_by(
                account_id=g.current_user['account_id']).first()
            if model is None or model.deleted:
                c_abort(404, message='Account Settings for account_id: %s does'
                        ' not exist' % str(g.current_user['account_id']))
            old_event_sender_email = model.event_sender_email
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input
            data, errors = account_settings_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            if old_event_sender_email != data.event_sender_email:
                # first remove old email if it exists
                if old_event_sender_email:
                    remove_result = remove_verified_identity(
                        old_event_sender_email)
                    if not remove_result['status']:
                        # if for some reason old email could not be removed
                        # then don't allow further processing
                        c_abort(422, message='Server busy, email could not be '
                                'updated', errors={'event_sender_email': [
                                    'Server busy, email could not be '
                                    'updated']})
                # verify new email
                verify_result = verify_email(data, reverify=True)
                data = verify_result['account_settings']
                extra_message = verify_result['extra_message']
            db.session.add(data)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (event_sender_email)=(example@example.com) already
                # exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Updated Account Settings for account_id: %s' %
                           str(model.account_id),
                'extra_message': extra_message}, 200

    @swag_from('swagger_docs/account_settings_get.yml')
    def get(self):
        """
        Get account settings
        """
        account_settings_schema = AccountSettingsSchema()
        model = None
        try:
            # first find model
            model = AccountSettings.query.options(joinedload(
                AccountSettings.account)).filter_by(
                account_id=g.current_user['account_id']).first()
            if model is None or model.deleted:
                c_abort(404, message='Account Settings for account_id: %s does'
                        ' not exist' % str(g.current_user['account_id']))
            result = account_settings_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class VerifySenderEmailAPI(AuthResource):
    """
    Verifies the sender email
    """

    @swag_from('swagger_docs/verify_sender_email_api_put.yml')
    def put(self):
        """
        Verifies the sender email, and update account settings accordingly
        """
        # first find model
        model = None
        try:
            model = AccountSettings.query.options(joinedload(
                AccountSettings.account)).filter_by(
                account_id=g.current_user['account_id']).first()
            if model is None or model.deleted:
                c_abort(404, message='Account Settings for account_id: %s does'
                        ' not exist' % str(g.current_user['account_id']))
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        # if sender email not set, nothing to do
        if not model.event_sender_email:
            c_abort(422, message='Sender email not set, nothing to verify',
                    errors={'event_sender_email': ['Sender email not set, '
                                                   'nothing to verify']})

        try:
            # verify the email
            verify_result = verify_email(model, reverify=True)
            model = verify_result['account_settings']
            extra_message = verify_result['extra_message']
            db.session.add(model)
            db.session.commit()
        except HTTPException as e:
            raise e
        except Forbidden as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Updated Account Settings for account_id: %s' %
                           str(model.account_id),
                'extra_message': extra_message}, 200


class RemoveVerifySenderEmailAPI(AuthResource):
    """
    Remove or reset Verifies the sender email, and update account settings
    accordingly
    """

    def put(self):
        """
        reset Verifies the sender email
        """
        # first find model
        model = None
        try:
            model = AccountSettings.query.options(joinedload(
                AccountSettings.account)).filter_by(
                account_id=g.current_user['account_id']).first()
            if model is None or model.deleted:
                c_abort(404, message='Account Settings for account_id: %s does'
                        ' not exist' % str(g.current_user['account_id']))
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        # if sender email not set, nothing to do
        if not model.event_sender_email:
            c_abort(422, message='Sender email not set, nothing to verify',
                    errors={'event_sender_email': ['Sender email not set, '
                                                   'nothing to verify']})
        try:
            # first remove old email if it exists
            remove_result = remove_verified_identity(model.event_sender_email)
            if not remove_result['status']:
                # if for some reason old email could not be removed
                # then don't allow further processing
                c_abort(422, message='Server busy, email could not be '
                                     'updated',
                        errors={'event_sender_email': [
                            'Server busy, email could not be '
                            'updated']})
            model.event_sender_email = None
            model.event_sender_name = None
            model.event_sender_verified = False
            model.event_sender_domain_verified = False
            db.session.add(model)
            db.session.commit()
        except HTTPException as e:
            raise e
        except Forbidden as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Reset Account Settings for account_id: %s' %
                           str(model.account_id)}, 200
