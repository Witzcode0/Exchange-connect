"""
API endpoints for "activities Institution" package.
"""
from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from sqlalchemy import and_, any_, func, or_, literal
from app import db, c_abort

from config import SQLALCHEMY_EXTERNAL_DATABASE_URI
from sqlalchemy import create_engine
from app.base.api import AuthResource, BaseResource, load_current_user
from sqlalchemy.sql import text
from app.activity.activities_institution.schemas import (
    ActivityInstitutionFactSetSchema,
    ActivityFactSetReadArgsSchema)


class ActivityIntituteFactSetList(AuthResource):
    """
    Read API for fact set list lists, i.e, more than 1 activity
    """
    model_class = None

    ext_db = create_engine(SQLALCHEMY_EXTERNAL_DATABASE_URI).connect()

    def __init__(self, *args, **kwargs):
        super(ActivityIntituteFactSetList, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        factset_data = []
        processed_data = []
        if filters:
            if 'full_name' in filters and 'factset_institution_id' in filters:
                factset_data = self.ext_db.execute(
                    text("getpeoplename_byinstitution '%s', '%s'"%(
                        filters['full_name'],filters['factset_institution_id']))).fetchall()
        for data in factset_data:
            fact_dict= {}
            fact_dict['factset_participant_id'] = data[0]
            fact_dict['full_name'] = data[1]
            fact_dict['designation'] = data[2]
            fact_dict['account_name'] = data[3]
            fact_dict['email'] = data[4]

            processed_data.append(fact_dict)

        return processed_data, pagination

    def get(self):
        """
        Get the list
        """
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            ActivityFactSetReadArgsSchema(strict=True))
        try:
            # build the sql query
            list_data, pagination =\
                self.build_query(filters, pfields, sort, pagination,
                                 None, operator)
            # making a copy of the main output schema
            factset_schema = ActivityInstitutionFactSetSchema()
            total = len(list_data)
            if not list_data:
                c_abort(404, message='No matching Factset ids found')
            result = factset_schema.dump(list_data, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            c_abort(403, message='Not allowed, User has not given '
                            'permission')
        return {'results': result.data, 'total': total}, 200