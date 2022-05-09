"""
API endpoints for "Email event static" package.
"""

from flask import request, current_app, g

from app import db, c_abort
from app.base.api import AuthResource, BaseResource
from app import es
import uuid
import json
from datetime import date, timedelta

from app.resources.email_statics.models import EmailStatics
from app.resources.email_statics.schemas import (EmailStaticsSchema,
    EmailStaticsReadArgSchema)
from sqlalchemy.exc import IntegrityError
from app.base import constants as APP
from flask_restful import abort
from app import db, c_abort, distributionlistfile
from werkzeug.exceptions import Forbidden, HTTPException
from sqlalchemy.inspection import inspect
from sqlalchemy import Date, cast, func
from sqlalchemy import or_, and_

from app.resources.users.models import User
from app.resources.user_profiles.models import UserProfile
from app.news_letter.distribution_list.models import DistributionList
from app.resources.accounts.models import Account


class EmailStatic(BaseResource):
    """
    Create API for email statics
    """

    def post(self):
        """
        Create event bookmark
        """
        data = request.get_data().decode('utf-8')
        current_app.logger.exception("+"*10,data)
        json_d = {'data':data}
        dumped_data= json.dumps(data)
        json_data = json.loads(json.loads(dumped_data))
        if not json_data:
            c_abort(400)
#        json_d = {'data':data}
        index = 'ses_imp'
        if not es.indices.exists(index=index):
            es.indices.create(index = index)
        res = es.index(index = index, doc_type= index, id=uuid.uuid1().int, body = json_d)
        if json_data['Type'] == 'Notification':
            """ check for notification type"""

            try:
                message_data = json.loads(json_data['Message'])
                message_data_type = 'dict'
            except:
                message_data_type = 'str'
            if message_data_type == 'dict':
                """ define schema for email statics"""

                email_notification_schema = EmailStaticsSchema()

                if message_data['eventType'] == "Send":
                    """ method for send event """

                    # model = EmailStatics.query.filter_by(
                    #         message_id=message_data['mail']['messageId']).first()

                    email_data = dict()
                    email_data['message_id'] = message_data['mail']['messageId']
                    email_data['email'] = message_data['mail']['destination'][0]
                    email_data['date'] = message_data['mail']['timestamp'].split("T")[0]
                    email_data['send'] = (message_data['mail']['timestamp'].split("T")[0]
                        +" "+message_data['mail']['timestamp'].split("T")[1].split(".")[0])

                    for elem in message_data['mail']['headers']:
                        if elem['name'] == "From":
                            email_data['from_email'] = elem['value']
                        elif elem['name'] == "To":
                            email_data['to_email'] = elem['value']
                            # distribution user filteration
                            user = DistributionList.query.filter_by(email=elem['value']).first()
                            if not user:
                                # user filteration
                                user = User.query.filter_by(email=elem['value']).first()
                                if not user:
                                    c_abort(404, message='user does not exist')
                                if user:
                                    email_data['user_id'] = user.row_id
                                    user_profile = UserProfile.query.filter_by(
                                        user_id=user.row_id).first()
                                    email_data['first_name'] = user_profile.first_name
                                    email_data['last_name'] = user_profile.last_name
                                    account = Account.query.filter_by(
                                            row_id=user.account_id).first()
                                    email_data['account_name'] = account.account_name
                                    email_data['account_type'] = account.account_type
                            else:
                                email_data['dic_user_id'] = user.row_id
                                email_data['first_name'] = user.first_name
                                email_data['last_name'] = user.last_name
                                account = Account.query.filter_by(
                                    row_id=user.account_id).first()
                                email_data['account_name'] = account.account_name
                                email_data['account_type'] = account.account_type
                                # email_data['account_id'] = user.account_id

                        elif elem['name'] == "keywords":
                            if elem['value']:
                                email_data['email_category'] = elem['value']

                        elif elem['name'] == "Subject":
                            email_data['subject'] = elem['value']
                    try:
                        # validate and deserialize input into object
                        data, errors = email_notification_schema.load(email_data)
                        if errors:
                            c_abort(422, errors=errors)
                        db.session.add(data)
                        db.session.commit()
                    except IntegrityError as e:
                        db.session.rollback()
                        if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                            # format of the message:
                            # Key (lower(name::text))=(abc) already exists.
                            column = e.orig.diag.message_detail.split('(')[2].split(':')[0]
                            c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                                column: [APP.MSG_ALREADY_EXISTS]})
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

                    return {'message': 'record created'}, 201

                if message_data['eventType'] == "Delivery":
                    """ method for delivery event """

                    email_data = dict()
                    deliver_time = message_data['delivery']['timestamp'].split("T")
                    email_data['delivery'] = (deliver_time[0]
                        +" "+deliver_time[1].split(".")[0])

                    model = None
                    try:
                        # fine model using messageid
                        model = EmailStatics.query.filter_by(
                            message_id=message_data['mail']['messageId']).first()
                        if model is None:
                            c_abort(404, message='message_id does not exist')
                    except HTTPException as e:
                        raise e
                    except Exception as e:
                        current_app.logger.exception(e)
                        abort(500)

                    try:
                        # validate and deserialize input
                        data, errors = email_notification_schema.load(
                            email_data, instance=model, partial=True)

                        if errors:
                            c_abort(422, errors=errors)

                        if data.bounce:
                            data.bounce = None

                        if data.reject:
                            data.reject = None

                        db.session.add(data)
                        db.session.commit()
                    except IntegrityError as e:
                        db.session.rollback()
                        if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                            # format of the message:
                            # Key (country_id, state_id, city_name)=(1, 1, Hyd)
                            # already exists.
                            column = e.orig.diag.message_detail.split('(')[2].split(':')[0]
                            c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                                column: [APP.MSG_ALREADY_EXISTS]})
                        if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                            # format of the message:
                            # Key (country_id)=(2) is not present in table "country".
                            # Key (state_id)=(3) is not present in table "state".
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
                    return {'message': 'Message update'}, 200

                if message_data['eventType'] == "Open":
                    """ method for open event """

                    email_data = dict()
                    open_time = message_data['open']['timestamp'].split("T")
                    email_data['open_time'] = (open_time[0]
                        +" "+open_time[1].split(".")[0])
                    email_data['ip_address'] = message_data['open']['ipAddress']
                    email_data['userAgent'] = message_data['open']['userAgent']

                    model = None
                    try:
                        # fine model using messageid
                        model = EmailStatics.query.filter_by(
                            message_id=message_data['mail']['messageId']).first()
                        if model is None or not model.delivery:
                            c_abort(404, message='message_id does not exist')
                    except HTTPException as e:
                        raise e
                    except Exception as e:
                        current_app.logger.exception(e)
                        abort(500)
                    try:
                        # validate and deserialize input
                        data, errors = email_notification_schema.load(
                            email_data, instance=model, partial=True)
                        if errors:
                            c_abort(422, errors=errors)
                        db.session.add(data)
                        db.session.commit()
                    except IntegrityError as e:
                        db.session.rollback()
                        if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                            # format of the message:
                            # Key (country_id, state_id, city_name)=(1, 1, Hyd)
                            # already exists.
                            column = e.orig.diag.message_detail.split('(')[2].split(':')[0]
                            c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                                column: [APP.MSG_ALREADY_EXISTS]})
                        if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                            # format of the message:
                            # Key (country_id)=(2) is not present in table "country".
                            # Key (state_id)=(3) is not present in table "state".
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
                    return {'message': 'Message update'}, 200

                if message_data['eventType'] == "Click":
                    """ method for click event """

                    email_data = dict()
                    open_time = message_data['click']['timestamp'].split("T")
                    email_data['click'] = (open_time[0]
                        +" "+open_time[1].split(".")[0])

                    model = None
                    try:
                        # fine model using messageid
                        model = EmailStatics.query.filter_by(
                            message_id=message_data['mail']['messageId']).first()
                        if model is None or not model.delivery:
                            c_abort(404, message='message_id does not exist')
                    except HTTPException as e:
                        raise e
                    except Exception as e:
                        current_app.logger.exception(e)
                        abort(500)
                    try:
                        # validate and deserialize input
                        data, errors = email_notification_schema.load(
                            email_data, instance=model, partial=True)
                        if errors:
                            c_abort(422, errors=errors)

                        if not data.open_time:
                            data.open_time = (open_time[0]+" "+open_time[1].split(".")[0])
                        db.session.add(data)
                        db.session.commit()
                    except IntegrityError as e:
                        db.session.rollback()
                        if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                            # format of the message:
                            # Key (country_id, state_id, city_name)=(1, 1, Hyd)
                            # already exists.
                            column = e.orig.diag.message_detail.split('(')[2].split(':')[0]
                            c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                                column: [APP.MSG_ALREADY_EXISTS]})
                        if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                            # format of the message:
                            # Key (country_id)=(2) is not present in table "country".
                            # Key (state_id)=(3) is not present in table "state".
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
                    return {'message': 'Message update'}, 200

                if message_data['eventType'] == "Reject":
                    """ method for reject event """

                    email_data = dict()
                    email_data['message_id'] = message_data['mail']['messageId']
                    email_data['email'] = message_data['mail']['destination'][0]
                    email_data['date'] = message_data['mail']['timestamp'].split("T")[0]
                    email_data['reject'] = (message_data['reject']['timestamp'].split("T")[0]
                        +" "+message_data['reject']['timestamp'].split("T")[1].split(".")[0])

                    for elem in message_data['mail']['headers']:
                        if elem['name'] == "From":
                            email_data['from_email'] = elem['value']
                        elif elem['name'] == "To":
                            email_data['to_email'] = elem['value']
                            # distribution user filteration
                            user = DistributionList.query.filter_by(email=elem['value']).first()
                            if not user:
                                user = User.query.filter_by(email=elem['value']).first()
                                if not user:
                                    c_abort(404, message='user does not exist')
                                if user:
                                    email_data['user_id'] = user.row_id
                                    user_profile = UserProfile.query.filter_by(
                                        user_id=user.row_id).first()
                                    email_data['first_name'] = user_profile.first_name
                                    email_data['last_name'] = user_profile.last_name
                                    account = Account.query.filter_by(
                                            row_id=user.account_id).first()
                                    email_data['account_name'] = account.account_name
                                    email_data['account_type'] = account.account_type
                            else:
                                email_data['dic_user_id'] = user.row_id
                                email_data['first_name'] = user.first_name
                                email_data['last_name'] = user.last_name
                                account = Account.query.filter_by(
                                    row_id=user.account_id).first()
                                email_data['account_name'] = account.account_name
                                email_data['account_type'] = account.account_type

                        elif elem['name'] == "keywords":
                            if elem['value']:
                                email_data['email_category'] = elem['value']

                        elif elem['name'] == "Subject":
                            email_data['subject'] = elem['value']

                    try:
                        # validate and deserialize input into object
                        data, errors = email_notification_schema.load(email_data)
                        if errors:
                            c_abort(422, errors=errors)
                        db.session.add(data)
                        db.session.commit()
                    except IntegrityError as e:
                        db.session.rollback()
                        if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                            # format of the message:
                            # Key (lower(name::text))=(abc) already exists.
                            column = e.orig.diag.message_detail.split('(')[2].split(':')[0]
                            c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                                column: [APP.MSG_ALREADY_EXISTS]})
                        # for any other unknown db errors
                        current_app.logger.exception(e)
                        abort(500)

                    return {'message': 'json add sucessfully'},201
                    # return True

                if message_data['eventType'] == "Bounce":
                    """ method for bounce event """

                    model = None
                    try:
                        # fine model using messageid
                        model = EmailStatics.query.filter_by(
                            message_id=message_data['mail']['messageId']).first()
                        if model is None:
                            c_abort(404, message='message_id does not exist')
                    except HTTPException as e:
                        raise e
                    except Exception as e:
                        current_app.logger.exception(e)
                        abort(500)

                    if not model.delivery:
                        try:
                            # validate and deserialize input
                            email_data = dict()
                            email_data['bounce'] = (message_data['bounce']['timestamp'].split("T")[0]
                                +" "+message_data['bounce']['timestamp'].split("T")[1].split(".")[0])
                            data, errors = email_notification_schema.load(
                                email_data, instance=model, partial=True)

                            if errors:
                                c_abort(422, errors=errors)
                            db.session.add(data)
                            db.session.commit()
                        except IntegrityError as e:
                            db.session.rollback()
                            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                                # format of the message:
                                # Key (country_id, state_id, city_name)=(1, 1, Hyd)
                                # already exists.
                                column = e.orig.diag.message_detail.split('(')[2].split(':')[0]
                                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                                    column: [APP.MSG_ALREADY_EXISTS]})
                            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                                # format of the message:
                                # Key (country_id)=(2) is not present in table "country".
                                # Key (state_id)=(3) is not present in table "state".
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
                    return {'message': 'Message update'}, 200

                if message_data['eventType'] == "Complaint":
                    """ method for complaint event """

                    email_data = dict()
                    complaint_time = message_data['complaint']['timestamp'].split("T")
                    email_data['complaint'] = (complaint_time[0]
                        +" "+complaint_time[1].split(".")[0])

                    model = None
                    try:
                        # find model using messageid
                        model = EmailStatics.query.filter_by(
                            message_id=message_data['mail']['messageId']).first()
                        if model is None:
                            c_abort(404, message='message_id does not exist')
                    except HTTPException as e:
                        raise e
                    except Exception as e:
                        current_app.logger.exception(e)
                        abort(500)

                    try:
                        # validate and deserialize input
                        data, errors = email_notification_schema.load(
                            email_data, instance=model, partial=True)

                        if errors:
                            c_abort(422, errors=errors)
                        db.session.add(data)
                        db.session.commit()
                    except IntegrityError as e:
                        db.session.rollback()
                        if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                            # format of the message:
                            # Key (country_id, state_id, city_name)=(1, 1, Hyd)
                            # already exists.
                            column = e.orig.diag.message_detail.split('(')[2].split(':')[0]
                            c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                                column: [APP.MSG_ALREADY_EXISTS]})
                        if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                            # format of the message:
                            # Key (country_id)=(2) is not present in table "country".
                            # Key (state_id)=(3) is not present in table "state".
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
                    return {'message': 'Message update'}, 200

                    return {'message': 'json add sucessfully'},201
                    # return True

        return {'message':"this is not mail notification"}

class EmailStaticListAPI(AuthResource):
    """
    Read API for email statics lists, i.e, more than 1 record
    """
    model_class = EmailStatics

    def __init__(self, *args, **kwargs):
        super(EmailStaticListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        query_filters, extra_query, db_projection, s_projection, order, \
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)
        # build specific extra queries filters

        started_at = None
        ended_to = None

        if extra_query:
            if "from_date" in extra_query and extra_query['from_date']:
                started_at = extra_query.pop('from_date')
            if "to_date" in extra_query and extra_query['to_date']:
                ended_to = extra_query.pop('to_date')
            if 'full_name' in extra_query and extra_query['full_name']:
                full_name = '%' + (extra_query["full_name"]).lower() + '%'
                query_filters['filters'].append(func.lower(func.concat(EmailStatics.first_name, ' ',
                    EmailStatics.last_name)).like(full_name))
            if 'domain_id' in extra_query and extra_query['domain_id']:
                domain_id = extra_query.pop('domain_id')
                query_filters['filters'].append(Account.domain_id == domain_id)

        query = self._build_final_query(
            query_filters, query_session, operator)

        query = query.join(Account, Account.account_name == EmailStatics.account_name)

        if started_at and ended_to:
            query = query.filter(and_(EmailStatics.date >= started_at,EmailStatics.date <= ended_to))
        elif started_at:
            query = query.filter(EmailStatics.date >= started_at)
        elif ended_to:
            query = query.filter(EmailStatics.date <= ended_to)

        if sort:
            for col in sort['sort_by']:
                if col == 'full_name':
                    mapper = inspect(EmailStatics)
                    col = 'first_name'
                    sort_fxn = 'asc'
                    if sort['sort'] == 'dsc':
                        sort_fxn = 'desc'
                    order.append(getattr(mapper.columns[col], sort_fxn)())

        return query, db_projection, s_projection, order, paging

    def get(self):
        """
        Get the list
        """
        designation_read_schema = EmailStaticsReadArgSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            designation_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(EmailStatics),
                                 operator)
            # making a copy of the main output schema
            comment_schema = EmailStaticsSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                comment_schema = EmailStaticsSchema(
                    only=s_projection)

            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching Logs found')
            result = comment_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data, 'total': total}, 200
