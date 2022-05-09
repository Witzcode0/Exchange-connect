"""
API endpoints for "ref event sub types" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from flasgger.utils import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.base import constants as APP
from app.corporate_access_resources.ref_event_types.models import \
    CARefEventType
from app.corporate_access_resources.ref_event_sub_types.models \
    import CARefEventSubType
from app.corporate_access_resources.ref_event_sub_types.schemas \
    import CARefEventSubTypeSchema, CARefEventSubTypeReadArgsSchema, \
    CARefEventSubTypeEditSchema
from app.corporate_access_resources.corporate_access_events.models import \
    CorporateAccessEvent


class CARefEventSubTypeAPI(AuthResource):
    """
    CRUD API for managing ref event sub types
    """
    @swag_from('swagger_docs/corporate_ref_event_sub_types_post.yml')
    def post(self):
        """
        Create a ref event sub types
        """
        refevent_subtypes_schema = CARefEventSubTypeSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = refevent_subtypes_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                #  Key (name)=(Ref sub event type1) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            elif APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (event_type_id)=(155) is not present in table
                # "corporate_access_ref_event_type".
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Reference Event sub types Added: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201

    @swag_from('swagger_docs/corporate_ref_event_sub_types_put.yml')
    def put(self, row_id):
        """
        Update a ref event sub types
        """
        refevent_subtypes_edit_schema = CARefEventSubTypeEditSchema()
        # first find model
        model = None
        try:
            model = CARefEventSubType.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Reference Event sub types'
                        ' id: %s does not exist' % str(row_id))
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
            data, errors = refevent_subtypes_edit_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                #  Key (name)=(Ref sub event type1) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            elif APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (event_type_id)=(155) is not present in table
                # "corporate_access_ref_event_type".
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
        return {'message': 'Updated Reference Event sub types id: %s' %
                str(row_id)}, 200

    @swag_from('swagger_docs/corporate_ref_event_sub_types_delete.yml')
    def delete(self, row_id):
        """
        Delete a ref event sub types
        """
        model = None
        sub_type = None
        try:
            # first find model
            model = CARefEventSubType.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Reference Event sub types '
                        'id: %s does not exist' % str(row_id))
            # check particular sub-type is used in event or not
            sub_type = CorporateAccessEvent.query.filter(
                CorporateAccessEvent.event_sub_type_id == row_id).first()
            if sub_type:
                c_abort(
                    422, message=APP.MSG_REF_OTHER_TABLE +
                    ' CorporateAccessEvent', errors={
                        'row_id': [APP.MSG_REF_OTHER_TABLE +
                                   ' CorporateAccessEvent']})
            model.deleted = True
            model.updated_by = g.current_user['row_id']
            db.session.add(model)
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

    @swag_from('swagger_docs/corporate_ref_event_sub_types_get.yml')
    def get(self, row_id):
        """
        Get a reference event sub types by id
        """
        refevent_subtypes_schema = CARefEventSubTypeSchema(
            exclude=CARefEventSubTypeSchema._default_exclude_fields)
        model = None
        try:
            # first find model
            model = CARefEventSubType.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Reference Event sub types '
                        'id: %s does not exist' % str(row_id))
            result = refevent_subtypes_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class CARefEventSubTypeListAPI(AuthResource):
    """
    Read API for ref event sub type lists, i.e, more than 1
    """
    model_class = CARefEventSubType

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['creator', 'event_type']
        super(CARefEventSubTypeListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)
        # build specific extra queries filters
        if extra_query:
            if 'is_meeting' in extra_query and not extra_query['is_meeting']:
                query_filters['filters'].append(
                    CARefEventType.is_meeting.is_(False))
            elif 'is_meeting' in extra_query and extra_query['is_meeting']:
                query_filters['filters'].append(
                    CARefEventType.is_meeting.is_(True))

        query = self._build_final_query(
            query_filters, query_session, operator)
        query = query.join(CARefEventType)
        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/corporate_ref_event_sub_types_get_list.yml')
    def get(self):
        """
        Get the list
        """
        refevent_subtypes_read_schema = CARefEventSubTypeReadArgsSchema(
            strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            refevent_subtypes_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(
                    filters, pfields, sort, pagination, db.session.query(
                        CARefEventSubType), operator)
            # making a copy of the main output schema
            refevent_subtypes_schema = CARefEventSubTypeSchema(
                exclude=CARefEventSubTypeSchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                refevent_subtypes_schema = CARefEventSubTypeSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(
                    404, message='No matching ref event sub types found')
            result = refevent_subtypes_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
