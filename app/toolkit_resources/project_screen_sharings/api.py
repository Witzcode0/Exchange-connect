"""
API endpoints for "project screen sharing" package.
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
from app.resources.accounts import constants as ACCOUNT
from app.toolkit_resources.projects.models import Project
from app.toolkit_resources.project_screen_sharings.models import (
    ProjectScreenSharing)
from app.toolkit_resources.project_screen_sharings.schemas import (
    ProjectScreenSharingSchema, ProjectScreenSharingReadArgsSchema)


class ProjectScreenSharingAPI(AuthResource):
    """
    CRUD API for project screen sharing
    """

    @swag_from('swagger_docs/project_screen_sharing_post.yml')
    def post(self):
        """
        create project screen sharing
        """

        project_screen_sharing_schema = ProjectScreenSharingSchema()
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = project_screen_sharing_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            data.sent_by = g.current_user['row_id']
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            # for account_id of project
            project = Project.query.get(data.project_id)
            data.account_id = project.account_id
            db.session.add(data)
            db.session.commit()
        except HTTPException as e:
            raise e
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (project_id)=(100) is not present in table "project".
                column = e.orig.diag.message_detail.split('(')[1].split(')')[0]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except Forbidden as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Project screen sharing Added: %s' % str(
            data.row_id), 'row_id': data.row_id}, 201

    @swag_from('swagger_docs/project_screen_sharing_put.yml')
    def put(self, row_id):
        """
        Update project screen sharing
        """
        project_screen_sharing_schema = ProjectScreenSharingSchema()
        model = None
        try:
            model = ProjectScreenSharing.query.get(row_id)
            if model is None:
                c_abort(
                    404, message='Project screen sharing id: %s '
                                 'does not exist' % str(row_id))
            # only current user can change project screen sharing
            if model.created_by != g.current_user['row_id']:
                c_abort(401)
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            data, errors = project_screen_sharing_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.edited = True
            data.updated_by = g.current_user['row_id']

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
        return {'message': 'Updated Project screen sharing id: %s' %
                           str(row_id)}, 200

    @swag_from('swagger_docs/project_screen_sharing_delete.yml')
    def delete(self, row_id):
        """
        Delete project screen sharing by id
        """
        model = None
        try:
            model = ProjectScreenSharing.query.get(row_id)
            if model is None:
                c_abort(
                    404, message='Project screen sharing id: %s'
                                 ' does not exist' % str(row_id))
            if model.created_by != g.current_user['row_id']:
                c_abort(401)

            db.session.delete(model)
            db.session.commit()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {}, 204

    @swag_from('swagger_docs/project_screen_sharing_get.yml')
    def get(self, row_id):
        """
        Get project screen sharing by id
        """
        project_screen_sharing_schema = ProjectScreenSharingSchema()
        model = None
        try:
            # first find model
            model = ProjectScreenSharing.query.get(row_id)
            if model is None:
                c_abort(
                    404, message='Project screen sharing id: %s'
                                 ' does not exist' % str(row_id))
            result = project_screen_sharing_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class ProjectScreenSharingListAPI(AuthResource):
    """
    Read API for project screen sharing lists, i.e, more than
    """

    model_class = ProjectScreenSharing

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['creator', 'project_parameter']
        super(ProjectScreenSharingListAPI, self).__init__(*args, **kwargs)

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
        if extra_query:
            pass

        if g.current_user['account_type'] != ACCOUNT.ACCT_ADMIN:
            query_filters['base'].append(
                ProjectScreenSharing.account_id == g.current_user[
                    'account_id'])

        query = self._build_final_query(query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/project_screen_sharing_get_list.yml')
    def get(self):
        """
        Get the list
        """
        project_screen_sharing_read_schema = \
            ProjectScreenSharingReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            project_screen_sharing_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(
                                     ProjectScreenSharing), operator)
            # making a copy of the main output schema
            project_screen_sharing_schema = ProjectScreenSharingSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                project_screen_sharing_schema = ProjectScreenSharingSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(
                    404, message='No matching project screen sharing found')
            result = project_screen_sharing_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
