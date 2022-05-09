"""
API endpoints for "project file comments" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from sqlalchemy.exc import IntegrityError
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.orm import load_only
from flasgger.utils import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.base import constants as APP
from app.toolkit_resources.project_file_comments.models import (
    ProjectFileComment)
from app.resources.users.models import User
from app.toolkit_resources.project_file_comments.schemas import (
    ProjectFileCommentSchema, ProjectFileCommentReadArgsSchema)


class ProjectFileCommentAPI(AuthResource):
    """
    Create, update, delete API for file comments
    """
    # @swag_from('swagger_docs/project_file_archive_post.yml')
    def post(self):
        """
        Create a file comment
        """
        project_file_comment_schema = ProjectFileCommentSchema()
        # get the json data from the request
        json_data = request.get_json()
        try:
            # validate and deserialize input into object
            data, errors = project_file_comment_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (project_id)=(425) is not present in table "project".
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

        return {'message': 'Comment Added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    # @swag_from('swagger_docs/project_file_archive_put.yml')
    def put(self, row_id):
        """
        Update a file comment, pass file data as json
        """
        project_file_comment_schema = ProjectFileCommentSchema()
        # first find model
        json_data = request.get_json()
        if not json_data:
            c_abort(400)
        try:
            model = ProjectFileComment.query.get(row_id)
            if model is None:
                c_abort(404, message='Comment id: %s does not exist' %
                                     str(row_id))
            # check ownership
            if g.current_user['row_id'] != model.created_by:
                abort(403)
            data, errors = project_file_comment_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            db.session.add(data)
            db.session.commit()

        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (project_id)=(425) is not present in table "project".
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Updated Comment id: %s' % str(row_id)}, 200

    # @swag_from('swagger_docs/project_file_archive_delete.yml')
    def delete(self, row_id):
        """
        Delete a file comment
        """
        try:
            # first find model
            model = ProjectFileComment.query.get(row_id)
            if model is None:
                c_abort(404, message='Comment id: %s does not exist' %
                                     str(row_id))
            # check ownership
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

    # @swag_from('swagger_docs/project_file_archive_get.yml')
    def get(self, row_id):
        """
        Get a project file comment by id
        """
        project_file_comment_schema = ProjectFileCommentSchema(
            exclude=ProjectFileCommentSchema._default_exclude_fields)
        try:
            # first find model
            model = ProjectFileComment.query.get(row_id)
            if model is None:
                c_abort(404, message='Comment id: %s does not exist' %
                                     str(row_id))
            # # check ownership
            # if model.created_by != g.current_user['row_id']:
            #     abort(403)
            result = project_file_comment_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result}, 200


class ProjectFileCommentListAPI(AuthResource):
    """
    Read API for project file comments, i.e, more than 1
    """
    model_class = ProjectFileComment

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['creator', 'project_archive_file']
        super(ProjectFileCommentListAPI, self).__init__(*args, **kwargs)

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
            pass

        query = self._build_final_query(query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/project_file_archive_get_list.yml')
    def get(self):
        """
        Get the list
        """
        project_file_comment_read_schema = ProjectFileCommentReadArgsSchema(
            strict=True)
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            project_file_comment_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(
                    filters, pfields, sort, pagination,
                    db.session.query(ProjectFileComment),
                    operator)
            # making a copy of the main output schema
            project_file_comment_schema = ProjectFileCommentSchema(
                exclude=ProjectFileCommentSchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                project_file_comment_schema = ProjectFileCommentSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)

            # prepare models for output dump
            models = []
            for m in full_query.items:
                models.append(m)
                for comment_reader in m.seen_comment_users:
                    if comment_reader.row_id == g.current_user['row_id']:
                        break
                else:
                    m.is_read = False
                    m.seen_comment_users.append(
                        User.query.get(g.current_user['row_id']))
                    db.session.add(m)
            db.session.commit()

            total = full_query.total
            if not models:
                c_abort(404, message='No matching comments found')
            result = project_file_comment_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
