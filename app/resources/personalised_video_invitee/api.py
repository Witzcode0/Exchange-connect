from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError

from app import db, c_abort
from app.auth.decorators import role_permission_required
from app.resources.roles import constants as ROLE
from app.base import constants as APP
from app.base.api import AuthResource, BaseResource
from app.resources.personalised_video_invitee.schemas import PersonalisedVideoInviteeSchema
from app.resources.personalised_video_invitee.models import PersonalisedVideoInvitee


class PersonalisedVideoInviteeAPI(AuthResource):
    """
        Create, update, delete API for "Personalised Video Module"
    """

    # @role_permission_required(perms=[ROLE.EPT_AA], roles=[ROLE.ERT_SU])
    def post(self):
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)
        try:
            # validate and deserialize input into object
            data, errors = PersonalisedVideoInviteeSchema().load(
                json_data)

            if errors:
                c_abort(422, errors=errors)

            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by

            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
        except HTTPException as e:
            raise e
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (news_url)=(http://www.scmp.com/rss/17/feed)
                # already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Invitee Added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    def put(self, row_id):
        """
        personalised invitee update method
        """
        personalised_video_invitee_schema = PersonalisedVideoInviteeSchema
        model = None
        try:
            model = PersonalisedVideoInvitee.query.get(row_id)
            if model is None:
                c_abort(404, message='Invitee id: %s does not exist' %
                                     str(row_id))
        except Forbidden as e:
            raise e
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
            data, errors = personalised_video_invitee_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)

            db.session.add(data)
            db.session.commit()

        except HTTPException as e:
            raise e
        except Forbidden as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Updated Invitee id: %s' % str(row_id)}, 200

    def delete(self, row_id):
        """
        Delete post by id
        """
        model = None
        try:
            model = PersonalisedVideoInvitee.query.get(row_id)
            if model is None:
                c_abort(404, message='Post id: %s does not exist' %
                                     str(row_id))
            if model.created_by != g.current_user['row_id']:
                c_abort(401)

            # model.deleted = True
            db.session.add(model)
            db.session.commit()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {}, 204

    def get(self, row_id):
        """
        Get Invitee by id
        """
        model = None
        try:
            model = PersonalisedVideoInvitee.query.get(row_id)
            if model is None:
                c_abort(404, message='Invitee id: %s does not exist' %
                                     str(row_id))
            result = PersonalisedVideoInviteeSchema(
                exclude=PersonalisedVideoInviteeSchema._default_exclude_fields).dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result}, 200