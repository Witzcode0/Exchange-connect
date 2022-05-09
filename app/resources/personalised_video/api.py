import datetime
import os
import json
import dateutil
from dateutil import parser
from webargs.flaskparser import parser
from werkzeug.exceptions import Forbidden, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only, joinedload,contains_eager
from sqlalchemy import func, and_, or_
from flask import request, current_app, g
from flask_restful import abort

from app import db, c_abort
from app.common.helpers import time_converter
from app.base import constants as APP
from app.base.schemas import BaseCommonSchema
from app.base.api import AuthResource, BaseResource
from app.resources.accounts.models import Account
from app.resources.personalised_video.schemas import PersonalisedVideoSchema
from app.resources.personalised_video.models import (PersonalisedVideoMaster)
from app.resources.personalised_video_invitee.models import PersonalisedVideoInvitee
from app.resources.personalised_video_logs.schemas import PersonalisedVideoLogsSchema
from app.resources.users.models import User
from app.resources.account_profiles.models import AccountProfile
# from app.resources.personalised_video_logs
from app.resources.personalised_video_invitee.schemas import PersonalisedVideoInviteeSchema
from app.common.helpers import verify_video_token
from app.resources.personalised_video_invitee import constants as PSTATUS
from queueapp.personalised_video_email_tasks import (send_invitee_interested_email,
                                                     send_invitee_interest_sales_email,
                                                     send_invitee_not_interested_email)


class PersonalisedVideoAPI(BaseResource):
    def get(self, token):
        """
        Get a video by token
        """
        personalised_video_schema = PersonalisedVideoSchema()
        model = None
        input_data = None
        video_data = None

        video_data = verify_video_token(token)
        video_id = None
        if video_data:
            video_invitee = PersonalisedVideoInvitee.query.filter(
                and_(
                    PersonalisedVideoInvitee.email == video_data['email'],
                    PersonalisedVideoInvitee.account_id == video_data['account_id']
                    )).join(PersonalisedVideoMaster, and_(func.lower(PersonalisedVideoMaster.video_type) == video_data["video_type"].lower(),
                                                          PersonalisedVideoMaster.row_id == PersonalisedVideoInvitee.video_id)).first()
            if video_invitee:
                video_id = video_invitee.video_id
                log_data = {}
                log_time = datetime.datetime.utcnow()
                log_data['video_id'] = video_invitee.video_id
                log_data['invitee_id'] = video_invitee.row_id
                log_data['email'] = video_data['email']
                if log_data:
                    try:
                        data, errors = PersonalisedVideoLogsSchema().load(log_data)
                        if errors:
                            print(errors)
                        data.interest_status = log_time
                        db.session.add(data)
                        db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                        print(e)
        else:
            c_abort(422, message='Token invalid', errors={
                'token': ['Token invalid']})

        try:
            """
            model = PersonalisedVideoMaster.query.filter(PersonalisedVideoMaster.row_id == video_id).join(
                PersonalisedVideoInvitee, and_(
                    PersonalisedVideoInvitee.video_id == PersonalisedVideoMaster.row_id,
                    PersonalisedVideoInvitee.email == video_data['email']),
                isouter=True).options(contains_eager(PersonalisedVideoMaster.external_invitees)).first()
            """
            model = PersonalisedVideoMaster.query.filter(PersonalisedVideoMaster.row_id == video_id,
                func.lower(PersonalisedVideoMaster.video_type) == video_data["video_type"].lower()).join(
                PersonalisedVideoMaster.external_invitees).\
                options(contains_eager(PersonalisedVideoMaster.external_invitees)).filter(and_(
                    PersonalisedVideoInvitee.video_id == PersonalisedVideoMaster.row_id,
                    PersonalisedVideoInvitee.email == video_data['email'])).all()

            # model = PersonalisedVideoMaster.query.filter(PersonalisedVideoMaster.row_id == video_id,
            #     func.lower(PersonalisedVideoMaster.video_type) == video_data["video_type"].lower()).join(
            #     PersonalisedVideoInvitee, and_(
            #         PersonalisedVideoInvitee.video_id == PersonalisedVideoMaster.row_id,
            #         PersonalisedVideoInvitee.email == video_data['email']),
            #     isouter=True).options(joinedload(PersonalisedVideoMaster.external_invitees)).first()
            if len(model) == 0:
                c_abort(404, message='Video File id: %s does not exist' %
                                     str(video_id))

            result = personalised_video_schema.dump(model[0])
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result}, 200

    def put(self, token):
        """
        Update interest status using token
        """
        personalised_video_schema = PersonalisedVideoSchema()
        personalised_video_invitee_schema = PersonalisedVideoInviteeSchema()

        video_data = None

        video_data = verify_video_token(token)
        if video_data:
            video_invitee = PersonalisedVideoInvitee.query.filter(
                and_(
                    PersonalisedVideoInvitee.email == video_data['email'],
                    PersonalisedVideoInvitee.account_id == video_data['account_id'])).\
                    join(PersonalisedVideoMaster,
                         and_(func.lower(PersonalisedVideoMaster.video_type) == video_data["video_type"].lower(),
                        PersonalisedVideoMaster.row_id == PersonalisedVideoInvitee.video_id)).first()
            if video_invitee:
                try:
                    invitee_model = PersonalisedVideoInvitee.query.get(video_invitee.row_id)

                    if invitee_model is None:
                        c_abort(
                            404,
                            message='video invitee email: %s does not exist' %
                                    video_data['email'])

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
                        json_data, instance=invitee_model, partial=True)

                    if errors:
                        c_abort(422, errors=errors)

                    db.session.add(data)
                    db.session.commit()
                    #write mailing task here
                    if data.video_status == PSTATUS.PVSTATUS_INTERESTED:
                        #write mail to user and sales team
                        send_invitee_interested_email.s(True, data.row_id).delay()
                        send_invitee_interest_sales_email.s(True, data.row_id).delay()
                    if data.video_status == PSTATUS.PVSTATUS_NOT_INTERESTED:
                        #write mail to user
                        send_invitee_not_interested_email.s(True, data.row_id).delay()

                except IntegrityError as e:
                    db.session.rollback()
                    if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                        # format of the message:
                        # Key (webcast_id, invitee_id, invitee_email)=
                        # (1, 1, keval@arham.com) already exists.
                        column = e.orig.diag.message_detail.split('(')[1][:-2]
                        c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                            column: [APP.MSG_ALREADY_EXISTS]})
                    if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                        column = e.orig.diag.message_detail.split('(')[1][:-2]
                        c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                            column: [APP.MSG_DOES_NOT_EXIST]})
                    # for any other unknown db errors
                    current_app.logger.exception(e)
                    abort(500)
                except Forbidden as e:
                    raise e
                except HTTPException as e:
                    raise e
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.exception(e)
                    abort(500)
                return {'message': 'Updated Webcast invitee id: %s' %
                                   video_data['email']}, 200
