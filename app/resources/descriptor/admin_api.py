"""
API endpoints for "descriptor master" package.
"""
from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy import and_, func
from sqlalchemy.orm import load_only, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy.inspection import inspect
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.base import constants as APP
from app.auth.decorators import role_permission_required
from app.resources.bse.models import BSEFeed
from app.resources.corporate_announcements.models import CorporateAnnouncement
from app.resources.corporate_announcements_category.models import CorporateAnnouncementCategory
from app.resources.descriptor.models import BSE_Descriptor
# from app.resources.bse.models import BSE_Descriptor
from app.resources.descriptor.schemas import AdminBseDescriptorSchema, BseDescriptorReadArgsSchema
from app.resources.roles import constants as ROLE


class AdminBSEDescriptorAPI(AuthResource):
    """
    For add descriptor and category id
    """

    def post(self):
        """
        Create descripor by admin
        """
        admin_bse_descriptor_schema = AdminBseDescriptorSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            data, errors = admin_bse_descriptor_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            # fetch last id of descriptor
            max_id = db.session.query(BSE_Descriptor.descriptor_id).order_by(
                BSE_Descriptor.descriptor_id.desc()).first()
            # add descriptor id for next descriptor
            data.descriptor_id = max_id[0] + 1
            db.session.add(data)
            db.session.commit()

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

        return {'message': 'Descriptor Added: %s' %
                           str(data.row_id), 'row_id': data.row_id}, 201

    def put(self, row_id):
        """
        Update descriptor by admin
        """

        admin_bse_descriptor_schema = AdminBseDescriptorSchema()
        model = None
        try:
            model = BSE_Descriptor.query.get(row_id)

            if model is None or model.deleted:
                c_abort(404, message='Corporate Announcement id: %s'
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
            data, errors = admin_bse_descriptor_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()

            # Change ec_category in bse_corp_feed for specific descriptor
            # bse_feeds = BSEFeed.query.filter(BSEFeed.descriptor_id == data.descriptor_id).all()
            # ec_category_to_update = []
            # for each_feed in bse_feeds:
            #     each_feed.ec_category = data.cat_id
            #     ec_category_to_update.append(each_feed)
            # if ec_category_to_update:
            #     db.session.add_all(ec_category_to_update)
            #     db.session.commit()

            # Change category_id in corporate_announcement for specific descriptor
            # corp_announcements = CorporateAnnouncement.query.\
            #     filter(CorporateAnnouncement.bse_descriptor == data.row_id).all()
            # category_id_to_update = []
            # for each_announcement in corp_announcements:
            #     each_announcement.category_id = data.cat_id
            #     category_id_to_update.append(each_announcement)
            # if category_id_to_update:
            #     db.session.add_all(category_id_to_update)
            #     db.session.commit()

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

        return {'message': 'Updated Descriptor id: %s' %
                           str(row_id)}, 200

    def delete(self, row_id):
        """
        Delete a bse descriptor by admin
        """
        model = None
        try:
            # first find model
            model = BSE_Descriptor.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Corporate Announcement id: %s'
                                     ' does not exist' % str(row_id))
            # if model is found, and not yet deleted, delete it
            model.updated_by = g.current_user['row_id']
            model.deleted = True
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
        return {'message': 'Deleted Descriptor id: %s' %
                           str(row_id)}, 204

    def get(self, row_id):
        """
        Get a bse descriptor request by id by admin
        """
        admin_bse_descriptor_schema = AdminBseDescriptorSchema()
        model = None
        try:
            # first find model with category name
            model = BSE_Descriptor.query.join(CorporateAnnouncementCategory,
                    BSE_Descriptor.cat_id == CorporateAnnouncementCategory.row_id)\
                    .filter(BSE_Descriptor.row_id == row_id)\
                    .first()
            # model returns as None if cat_id is null
            if model is None:
                model = BSE_Descriptor.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Descriptor, id: %s'
                                     ' does not exist' % str(row_id))
            result = admin_bse_descriptor_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class AdminBSEDescriptorListAPI(AuthResource):
    """
    Read API for descriptor list, i.e, more than 1 descriptor name
    """
    model_class = BSE_Descriptor

    def __init__(self, *args, **kwargs):
        super(
            AdminBSEDescriptorListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        # descriptor_name = None
        # if 'descriptor_name' in filters and filters['descriptor_name']:
        #     descriptor_name = filters.pop('descriptor_name')
        query_filters, extra_query, db_projection, s_projection, order, \
        paging = self._build_query(
            filters, pfields, sort, pagination, operator,
            include_deleted=include_deleted)
        # mapper = inspect(BSE_Descriptor)
        # build specific extra queries filters
        account_id = None

        query = self._build_final_query(
            query_filters, query_session, operator)

        # if sort:
        #     sort_fxn = 'asc'
        #     if sort['sort'] == 'dsc':
        #         sort_fxn = 'desc'
        #     for sby in sort['sort_by']:
        #         if sby in mapper.columns:
        #             order.append(getattr(mapper.columns[sby], sort_fxn)())

        return query, db_projection, s_projection, order, paging

    # @role_permission_required(perms=[ROLE.ERT_AD], roles=[
    #     ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    @swag_from('swagger_docs/admin_corporate_announcement_get_list.yml')
    def get(self):
        """
        Get the list by admin
        """
        # schema for reading get arguments
        admin_bse_descriptor_read_schema = BseDescriptorReadArgsSchema(
            strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            admin_bse_descriptor_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(BSE_Descriptor),
                                 operator)
            # making a copy of the main output schema
            admin_bse_descriptor_schema = AdminBseDescriptorSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                admin_bse_descriptor_schema = AdminBseDescriptorSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching Descriptor found')
            result = admin_bse_descriptor_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200

