"""
API endpoints for "e_meeting" package.
"""
from flask import request, current_app, g
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import Forbidden, HTTPException
from flask_restful import abort
from sqlalchemy.orm import load_only
from sqlalchemy.orm import load_only, joinedload, contains_eager

from app import db, c_abort
from app.base.api import AuthResource
from app.base import constants as APP
from app.toolkit_resources.project_e_meeting_comment.models import (
    EmeetingComment)
from app.toolkit_resources.project_e_meeting_invitee.models import (
    EmeetingInvitee)
from app.toolkit_resources.project_e_meeting.models import (
    Emeeting)
from app.toolkit_resources.project_e_meeting_comment import constants as COMMENT
from app.toolkit_resources.project_e_meeting_comment.schemas import (
    EMeetingCommentSchema, EmeetingCommentReadArgsSchema)


class EmeetingCommentAPI(AuthResource):
    """
    CRUD API for managing Emeeting Comment
    """

    def post(self):
        """
        Create a Emeeting comment
        """
        e_meeting_comment_schema = EMeetingCommentSchema(strict=True)
        json_data = request.get_json()

        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            # remove all files when come as string
            data, errors = e_meeting_comment_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()

            if data.status == COMMENT.CANCEL:
                meeting_obj = Emeeting.query.get(data.e_meeting_id)
                meeting_obj.cancelled = True
                db.session.add(meeting_obj)
                db.session.commit()

        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                column = e.orig.diag.message_detail.split('(')[1].split(')')[0]
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
        return {'message': 'E_meeting comment created: %s' %
                           str(data.row_id), 'row_id': data.row_id}, 201

    def delete(self, row_id):
        """
        Delete a Emeeting
        """
        model = None
        try:
            # first find model
            model = EmeetingComment.query.get(row_id)
            if model is None:
                c_abort(404, message='Emeeting Comment id: %s does not exist' %
                                     str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            if model.deleted:
                c_abort(422, message='Emeeting Comment already deleted')

            model.deleted = True
            db.session.commit()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            abort(500)
        return {}, 204

    def get(self, row_id):
        """
        Get a Emeeting by id
        """
        model = None
        try:
            # first find model
            model = EmeetingComment.query.filter(
                EmeetingComment.row_id == row_id).first()
            if model is None:
                c_abort(404, message='Emeeting Comment id:'
                        ' %s does not exist' % str(row_id))
            # check ownership
            # for invitee users
            invitee_user_ids = []
            for meeting in EmeetingInvitee.query.filter(
                    EmeetingInvitee.e_meeting_id == model.e_meeting_id):
                if meeting.invitee_id:
                    invitee_user_ids.append(meeting.invitee_id)
            invitee_user_ids.append(model.created_by)

            if (g.current_user['row_id'] not in invitee_user_ids):
                abort(403)

            local_exclude_list = EMeetingCommentSchema._default_exclude_fields[:]

            result = EMeetingCommentSchema(
                exclude=local_exclude_list).dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class EmeetingCommentListAPI(AuthResource):
    """
    Read API for Emeeting lists, i.e, more than 1
    """
    model_class = EmeetingComment

    def __init__(self, *args, **kwargs):
        super(EmeetingCommentListAPI, self).__init__(*args, **kwargs)

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

        query = self._build_final_query(
            query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    def get(self):
        """
        Get the list
        """
        e_meeting_comment_read_schema = EmeetingCommentReadArgsSchema(
            strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            e_meeting_comment_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(EmeetingComment), operator)
            # making a copy of the main output schema
            local_exclude_list = EMeetingCommentSchema._default_exclude_fields[:]

            e_meeting_comment_schema = EMeetingCommentSchema(
                exclude=local_exclude_list)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                e_meeting_comment_schema = EMeetingCommentSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching meeting found')
            result = e_meeting_comment_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            abort(500)
        return {'results': result.data, 'total': total}, 200
