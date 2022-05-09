"""
API endpoints for "market performance API" package.
"""
import datetime
import pandas as pd

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from sqlalchemy.orm import load_only, joinedload
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_
from sqlalchemy import Date, cast

from app import db, c_abort, accountmarketperformancefile
from app.common.helpers import save_files_locally
from app.base.api import AuthResource
from app.market_resources.market_performance.models import (
    MarketPerformance)
from app.market_resources.market_performance.schemas import (
    MarketPerformanceSchema, MarketPerformanceReadArgsSchema)
from app.resources.accounts.models import Account
from app.resources.users.models import User


class MarketPerformanceAPI(AuthResource):
    """
    For creating Market Comment 
    """

    def post(self):
        """
        Create corporate announcement
        """
        all_errors = {}
        try:
            # create list of market performance from xls file

            fpath, fname, ferrors = save_files_locally(
                accountmarketperformancefile, request.files['file'])
            if ferrors:
                return ferrors
            data = pd.read_excel(fpath)
            for i in data.keys():
                data.rename(columns={i: i.strip()}, inplace=True)
            data.rename(columns={
                'Company': 'account_sort_name',
                'OPEN': 'open_price',
                'HIGH': 'high_price',
                'LOW': 'low_price',
                'PREV. CLOSE': 'prev_close_price',
                'CLOSE': 'ltp_price',
                'CHNG': 'chng_price',
                '52W H': 'h_price_52w',
                '52W L': 'l_price_52w'
            }, inplace=True)
            performance_list = []
            for j in range(len(data)):
                performance_dict = {}
                for i in data.keys():
                    str_data = str(data[i][j])
                    if i != 'account_sort_name':
                        if '.' in str_data:
                            int_data = float(str_data)
                            str_data = "%.2f"%int_data
                    performance_dict[i] = str_data
                performance_list.append(performance_dict)

            # delete existing data for same date
            performances_ids = MarketPerformance.query.filter(cast(
                MarketPerformance.created_date, Date) ==
                datetime.datetime.now().date()).delete(
                synchronize_session=False)
            db.session.commit()

            # create new data generate
            market_performance_schema = MarketPerformanceSchema()
            for performance in performance_list:
                account_int = Account.query.filter(
                    Account.isin_number == performance['ISIN']).first()
                if account_int or 'NIFTY 50' in performance[
                        'account_sort_name']:
                    json_data = performance
                    if account_int:
                        json_data.update({
                            "account_id": account_int.row_id})
                    if 'NIFTY 50' in performance['account_sort_name']:
                        json_data.update({
                            "account_id_null_boolean": True})
                    data, errors = market_performance_schema.load(
                        json_data)
                    if errors:
                        c_abort(422, errors=errors)
                    data.created_by = g.current_user['row_id']
                    data.updated_by = data.created_by

                    db.session.add(data)
                    db.session.commit()

        except HTTPException as e:
            raise e

        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Market Permission created'}, 201

    def delete(self, row_id):
        """
        Delete a Market Comment
        """
        model = None
        try:
            # first find model
            model = MarketPerformance.query.get(row_id)
            if model is None:
                c_abort(404, message='Market permission id: %s'
                        ' does not exist' % str(row_id))
            if model.created_by != g.current_user['row_id']:
                abort(403)
            # if model is found, and not yet deleted, delete it
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
        return {}, 204

    def get(self, row_id):
        """
        Get a Market Comment request by id
        """
        model = None
        try:
            # first find model
            model = MarketPerformance.query.get(row_id)
            if model is None:
                c_abort(404, message='Market performance id: %s'
                                     ' does not exist' % str(row_id))
            result = MarketPerformanceSchema().dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class MarketPerformanceListAPI(AuthResource):
    """
    Read API for market comment lists, i.e, more than 1
    """
    model_class = MarketPerformance

    def __init__(self, *args, **kwargs):
        super(MarketPerformanceListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        date = None
        if 'created_date' in filters:
            date = filters.pop('created_date')
        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)
        # build specific extra queries filters
        performance_date = None
        account_id = None
        if extra_query:
            pass

        if date:
            query_filters['base'].append(
                cast(MarketPerformance.created_date, Date) == date)

        query = self._build_final_query(
            query_filters, query_session, operator)

        query = query.options(
            joinedload(MarketPerformance.creator).load_only(
                'row_id', 'account_id').joinedload(
                User.account).joinedload(Account.profile))

        return query, db_projection, s_projection, order, paging

    def get(self):
        """
        Get the list
        """
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            MarketPerformanceReadArgsSchema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(MarketPerformance),
                                 operator)
            # making a copy of the main output schema
            comment_schema = MarketPerformanceSchema(
                exclude=MarketPerformanceSchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                comment_schema = MarketPerformanceSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching Market performance found')
            result = comment_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
