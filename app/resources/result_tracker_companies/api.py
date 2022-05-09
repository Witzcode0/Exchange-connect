"""
 API for result-tracker-companies
"""
import json
from http.client import HTTPException

from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy import inspect, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from werkzeug.exceptions import Forbidden

from app.base import constants as APP

from app import c_abort, db
from app.base.api import AuthResource
from app.resources.accounts.models import Account
from app.resources.result_tracker_companies.models import ResultTrackerGroupCompanies
from app.resources.result_tracker_companies.schemas import ResultTrackerGroupCompaniesSchema, \
    ResultTrackerGroupCompaniesArgsSchema

from app.resources.corporate_announcements.models import CorporateAnnouncement
from app.resources.results.models import AccountResultTracker


class ResultTrackerGroupCompaniesAPI(AuthResource):
    """
    post request to add companies in group
    """

    def post(self):
        """
        Create a company in result tracker group
        """
        result_tracker_group_companies_schema = ResultTrackerGroupCompaniesSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            group_id = json_data['group_id']
            account_ids = json_data['account_ids']

            for idx, account_id in enumerate(account_ids):
                count_result_tracker_group_companies = db.session.query(ResultTrackerGroupCompanies). \
                    filter(and_(ResultTrackerGroupCompanies.group_id == group_id,
                                ResultTrackerGroupCompanies.user_id == g.current_user['row_id'],
                                ResultTrackerGroupCompanies.account_id == account_id)).all()

                if len(count_result_tracker_group_companies) >= 1:
                    # Only one account id passed
                    if len(account_ids) == 1:
                        return {'message': 'Company ' + APP.MSG_ALREADY_EXISTS}, 422
                    continue
                top_seq_id_group_company = ResultTrackerGroupCompanies.query. \
                    filter(and_(ResultTrackerGroupCompanies.group_id == group_id,
                                ResultTrackerGroupCompanies.user_id == g.current_user['row_id'])). \
                    order_by(ResultTrackerGroupCompanies.sequence_id.desc()).first()

                json_data['account_id'] = account_id
                json_data['sequence_id'] = 1 if not top_seq_id_group_company\
                    else top_seq_id_group_company.sequence_id + 1

                data, errors = result_tracker_group_companies_schema.load(json_data)
                if errors:
                    c_abort(422, errors=errors)

                data.user_id = g.current_user['row_id']
                db.session.add(data)
                db.session.commit()

        except IntegrityError as e:
            # format of the message:
            # Key (account_id)=(17) is not present in table account
            column = e.orig.diag.message_detail.split('(')[1][:-2]
            db.session.rollback()
            c_abort(422, message='Company ' + APP.MSG_ALREADY_EXISTS, errors={
                column: ['Company ' + APP.MSG_ALREADY_EXISTS]})
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Result tracker group company created: %s' %
                           str(data.row_id), 'row_id': data.row_id}, 201

    def put(self, row_id):
        """
        Update Result-Tracker group
        """
        result_tracker_group_companies_schema = ResultTrackerGroupCompaniesSchema()
        model = None
        try:
            model = ResultTrackerGroupCompanies.query.get(row_id)

            if model is None:
                c_abort(404, message='Result Tracker group company id: %s'
                                     ' does not exist' % str(row_id))
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
            # validate and deserialize input
            data, errors = result_tracker_group_companies_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)

            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
        except Forbidden as e:
            raise e
        except IntegrityError as e:
            # format of the message:
            # Key (account_id)=(17) is not present in table account
            column = e.orig.diag.message_detail.split('(')[1][:-2]
            db.session.rollback()
            c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                column: [APP.MSG_DOES_NOT_EXIST]})
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Updated Result Tracker group company id: %s' %
                           str(row_id)}, 200

    def get(self, row_id):
        """
        Get a result tracker group request by id
        """
        result_tracker_group_companies_schema = ResultTrackerGroupCompaniesSchema()
        model = None
        try:
            # first find model
            models = ResultTrackerGroupCompanies.query.filter(
                and_(ResultTrackerGroupCompanies.group_id == row_id,
                     ResultTrackerGroupCompanies.user_id == g.current_user['row_id'])). \
                order_by(ResultTrackerGroupCompanies.sequence_id).all()
            if models is None:
                c_abort(404, message='Result Tracker group company id: %s'
                                     ' does not exist' % str(row_id))
            result = result_tracker_group_companies_schema.dump(models, many=True)

            for idx, model in enumerate(models):
                account_result_tracker_model = AccountResultTracker.query.\
                    filter(AccountResultTracker.account_id == model.account_id).first()
                if result.data[idx]['account']['row_id'] == model.account_id:
                    if account_result_tracker_model:
                        result.data[idx]['concall_date'] = str(account_result_tracker_model.concall_date) if \
                            account_result_tracker_model.concall_date else None
                        result.data[idx]['concall_url'] = account_result_tracker_model.concall_bse_feed.attachment_url \
                            if account_result_tracker_model.concall_bse_feed else None
                        result.data[idx]['result_date'] = str(account_result_tracker_model.
                                                              result_intimation_feed.date_of_meeting) if \
                            account_result_tracker_model.result_intimation_feed else None
                        result.data[idx]['result_url'] = account_result_tracker_model.result_declaration_feed.\
                            attachment_url if account_result_tracker_model.result_declaration_feed else None
                    else:
                        result.data[idx]['concall_date'] = None
                        result.data[idx]['concall_url'] = None
                        result.data[idx]['result_date'] = None
                        result.data[idx]['result_url'] = None
            if result.data:
                total = len(result.data)
            else:
                return {'message': 'No matching records found.'}, 404
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200

    def delete(self, row_id):
        """
        Delete a result tracker group
        """
        model = None
        try:
            # first find model
            model = ResultTrackerGroupCompanies.query.get(row_id)
            if model is None:
                c_abort(404, message='Result Tracker Group Company id: %s'
                                     ' does not exist' % str(row_id))

            top_seq_id_group_company = ResultTrackerGroupCompanies.query.\
                filter(and_(ResultTrackerGroupCompanies.group_id == model.group_id,
                            ResultTrackerGroupCompanies.user_id == g.current_user['row_id'])).\
                order_by(ResultTrackerGroupCompanies.sequence_id.desc()).first()
            if model.row_id == top_seq_id_group_company.row_id:
                db.session.delete(model)
                db.session.commit()
            else:
                result_tracker_group_companies = ResultTrackerGroupCompanies.query.filter(
                    and_(ResultTrackerGroupCompanies.group_id == model.group_id,
                         ResultTrackerGroupCompanies.user_id == g.current_user['row_id'])).all()
                for each_group_company in result_tracker_group_companies:
                    if each_group_company.sequence_id == model.sequence_id:
                        db.session.delete(model)
                        continue
                    if each_group_company.sequence_id > model.sequence_id:
                        each_group_company.sequence_id -= 1
                        db.session.add(each_group_company)
                db.session.commit()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204


class ResultTrackerGroupCompaniesListAPI(AuthResource):
    """
    Read API for Result Tracker Group lists, i.e, more than 1 Group
    """
    model_class = ResultTrackerGroupCompanies

    def __init__(self, *args, **kwargs):
        super(
            ResultTrackerGroupCompaniesListAPI, self).__init__(*args, **kwargs)

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
        mapper = inspect(ResultTrackerGroupCompanies)
        # build specific extra queries filters
        account_id = None

        query = self._build_final_query(
            query_filters, query_session, operator)
        # TODO: Check this filter why this is used.
        query = query.join(CorporateAnnouncement, ResultTrackerGroupCompanies.account_id ==
                           CorporateAnnouncement.account_id)
        if sort:
            sort_fxn = 'asc'
            if sort['sort'] == 'dsc':
                sort_fxn = 'desc'
            for sby in sort['sort_by']:
                if sby in mapper.columns:
                    order.append(getattr(mapper.columns[sby], sort_fxn)())

        return query, db_projection, s_projection, order, paging

    def get(self):
        """
        Get the list of Result Tracker Group
        """
        # schema for reading get arguments
        result_tracker_group_companies_schema = ResultTrackerGroupCompaniesArgsSchema(
            strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            result_tracker_group_companies_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(ResultTrackerGroupCompanies),
                                 operator)

            # making a copy of the main output schema
            result_group_schema = ResultTrackerGroupCompaniesSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                result_group_schema = ResultTrackerGroupCompaniesSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching Result'
                                     ' Tracker Group Company found')
            result = result_group_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class ResultTrackerGroupCompaniesBulkEditAPI(AuthResource):
    """
    For update bulk result group companies
    """

    def put(self):
        """
        Update result groups
        """
        result_tracker_group_companies_schema = ResultTrackerGroupCompaniesSchema()
        model = None

        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        company_list = json_data['companylist']
        try:
            for company in company_list:
                if "row_id" in company.keys():
                    model = ResultTrackerGroupCompanies.query.get(company["row_id"])
                    if model is None:
                        c_abort(404, message='Result Tracker Group company id: %s'
                                             ' does not exist' % str(company["row_id"]))

                    data, errors = result_tracker_group_companies_schema.load(
                        company, instance=model, partial=True)
                    if errors:
                        c_abort(422, errors=errors)
                    # no errors, so add data to db
                    db.session.add(data)
                    db.session.commit()

        except Forbidden as e:
            raise e
        except IntegrityError as e:
            # format of the message:
            # Key (account_id)=(17) is not present in table account
            column = e.orig.diag.message_detail.split('(')[1][:-2]
            db.session.rollback()
            c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                column: [APP.MSG_DOES_NOT_EXIST]})
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Result Tracker group companies are updated'}, 200


class ResultTrackerGroupCompaniesBulkDeleteAPI(AuthResource):
    """
    For delete bulk result group companies
    """

    def put(self):

        model = None

        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)
        if not json_data["account_ids"]:
            c_abort(422, message='accounts do not exist')
        group_id = json_data['group_id']
        # account_ids is row_ids of result_tracker_group_companies
        account_list = json_data["account_ids"]
        try:
            companies = ResultTrackerGroupCompanies.query.filter(and_(
                ResultTrackerGroupCompanies.group_id == group_id,\
                ResultTrackerGroupCompanies.user_id == g.current_user['row_id'])).all()

            for account_id in account_list:
                # first find model
                model = ResultTrackerGroupCompanies.query.get(account_id)
                sequence_id = model.sequence_id
                if model is None:
                    return {'message': 'Result Tracker Group Company id:'
                                       ' %s account_id does not exist' % account_id}, 404
                # for company in companies:
                if model in companies:
                    companies.remove(model)
                    db.session.delete(model)
                    db.session.commit()

        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Result Tracker Group Companies are Deleted'}, 204
