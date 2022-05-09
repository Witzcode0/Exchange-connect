"""
Some API endpoints for "emails" package, related to "settings".
"""

from flask import request, current_app, g
from sqlalchemy.orm import joinedload
from werkzeug.exceptions import HTTPException

from app import db, c_abort
from app.base.api import AuthResource
from app.resources.email_credentials.models import EmailCredential
from app.resources.email_credentials.schemas import EmailCredentialSchema
from smtplib import SMTPResponseException, SMTPAuthenticationError
from werkzeug.exceptions import Forbidden

email_credential_schema = EmailCredentialSchema()


class EmailCredentialAPI(AuthResource):
    """
    Manage the email settings
    """

    def put(self):
        try:
            model = EmailCredential.query.options(joinedload(
                EmailCredential.user)).filter_by(
                created_by=g.current_user['row_id']).first()
            if model is None:
                return {'message':
                        'Email Credential for user id: %s does not exist' %
                        str(g.current_user['row_id'])}, 404
        except Exception as e:
            current_app.logger.exception(e)
            return {}, 500

        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            return {'message': 'No input data provided'}, 400

        try:
            smtp_password = None
            if 'smtp_password' in json_data:
                smtp_password = json_data['smtp_password']
                del json_data['smtp_password']
            if not smtp_password:
                # password is must
                c_abort(422, message='smtp_password is mandatory.')

            # validate and deserialize input
            data, errors = email_credential_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)

            # no errors, so add data to db
            if smtp_password:
                # new password is sent as non-empty
                data.encrypt_password(smtp_password)

            data.is_smtp_active = False
            db.session.add(data)
            db.session.commit()
            # send test mail
            data.send_test_mail()
            # if mail sent successfully then smtp will be active
            data.is_smtp_active = True
            db.session.commit()
        except HTTPException as e:
            raise e
        except Forbidden as e:
            raise e
        except SMTPAuthenticationError:
            return {'message': 'Please check username or password.'}, 422
        except SMTPResponseException as e:
            return {'errors': e.smtp_error.decode('utf-8')}, 422
        except ConnectionRefusedError:
            return {"message": "Please check smtp host/port"}, 422

        except Exception as e:
            error = str(e)
            if ('Name or service not known' in error
                    or 'Temporary failure in name resolution' in error):
                return {"message": "Please check smtp host"}, 422
            if 'Network is unreachable' in error:
                return {"message": "Please check smtp port"}, 422
            db.session.rollback()
            current_app.logger.exception(e)
            return {}, 500
        return {'message': 'Updated email credential of user id: %s' % str(
            g.current_user['row_id'])}, 200

    def get(self):
        """
        :return:
        """
        model = None
        try:
            # first find model
            model = EmailCredential.query.options(joinedload(
                EmailCredential.user)).filter_by(
                created_by=g.current_user['row_id']).first()
            if model is None:
                # if credential not found create it
                model = EmailCredential(
                    created_by=g.current_user['row_id'],
                    account_id=g.current_user['account_id'],
                    name=" ".join([g.current_user['profile']['first_name'],
                                   g.current_user['profile']['last_name']]),
                    from_email=g.current_user['email'])
                db.session.add(model)
                db.session.commit()

            result = email_credential_schema.dump(model)
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            return {}, 500

        return {'results': result}, 200

    def delete(self):
        """
        resets the email credentials
        """
        try:
            # first find model
            model = EmailCredential.query.options(joinedload(
                EmailCredential.user)).filter_by(
                created_by=g.current_user['row_id']).first()
            if model is None:
                return {'message':
                        'Email Credential for user id: %s does not exist' %
                        str(g.current_user['row_id'])}, 404

            model.smtp_username = None
            model.smtp_password = None
            model.smtp_host = None
            model.smtp_port = None
            model.is_ssl = False
            model.is_smtp_active = False
            db.session.add(model)
            db.session.commit()
        except Forbidden as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            return {}, 500
        return {}, 204

