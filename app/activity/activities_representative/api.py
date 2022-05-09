from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import load_only, joinedload
from sqlalchemy import and_, any_, func, or_, literal
from flask_sqlalchemy import Pagination
    
from app.base import constants as APP
from app import db, c_abort
from app.base.api import AuthResource
from app.activity.activities_representative.schemas import RepresentationSchema, RepresentationReadArgsSchema
from app.resources.user_profiles.models import UserProfile
from app.resources.users.models import User
from app.crm_resources.crm_contacts.models import CRMContact
from app.activity.activities_representative.models import ActivityRepresentative

class RepresentativeAPI(AuthResource):
    """
    search API for representatives
    """
    model_class = None

    def __init__(self, *args, **kwargs):
        super(RepresentativeAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        # query for user
        user_profile_query = db.session.query(UserProfile).with_entities(
            UserProfile.created_date, UserProfile.first_name, 
            UserProfile.account_id, UserProfile.last_name, 
            UserProfile.designation, UserProfile.row_id, 
            UserProfile.user_id, literal("user").label("record_type")) 
        
        # query for crm contact
        crm_contact_query = db.session.query(CRMContact).filter(
            or_(CRMContact.created_by == g.current_user['row_id'],
                    CRMContact.user_id == g.current_user['row_id'])).with_entities(
            CRMContact.created_date, CRMContact.first_name, 
            CRMContact.account_id, CRMContact.last_name, 
            CRMContact.designation, CRMContact.row_id,
            CRMContact.user_id,
            literal("contact").label("record_type")) 

        if filters:
            if 'full_name' in filters and filters['full_name']:
                full_name = '%' + (filters["full_name"]).lower() + '%'
                user_profile_query = user_profile_query.filter(func.concat(
                    func.lower(UserProfile.first_name), ' ',
                    func.lower(UserProfile.last_name)).like(full_name))
                crm_contact_query = crm_contact_query.filter(func.concat(
                    func.lower(CRMContact.first_name), ' ',
                    func.lower(CRMContact.last_name)).like(full_name))
            if 'account_id' in filters and filters['account_id']:
                account_id = filters['account_id']
                user_profile_query = user_profile_query.filter(
                    UserProfile.account_id == account_id)
                crm_contact_query = crm_contact_query.filter(
                    CRMContact.account_id == account_id)
        # merge user and distribution user query
        query = user_profile_query.union_all(crm_contact_query)
        # query = crm_contact_query.union(user_profile_query)

        final_query = query.order_by("record_type")
        
        return final_query,pagination

    def get(self):
        """
        Get the list
        """
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            RepresentationReadArgsSchema(strict=True))
        try:
            # build the sql query
            query, paging=\
                self.build_query(filters, pfields, sort, pagination,
                                 None,
                                 operator)

            # making a copy of the main output schema
            comment_schema = RepresentationSchema()
            query = query.limit(paging["per_page"]).offset((paging["page"] - 1) * paging["per_page"]).all()
            models = [m for m in query]
            total = len(models)
            if not models:
                c_abort(404, message='No matching representatives found')
            result = comment_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            c_abort(403, message='Not allowed, User has not given '
                            'permission')
        return {'results': result.data, 'total': total}, 200