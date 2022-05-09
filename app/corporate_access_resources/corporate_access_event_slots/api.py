"""
API endpoints for "corporate access event slots" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only, joinedload
from flasgger.utils import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.base import constants as APP
from app.corporate_access_resources.corporate_access_event_inquiries \
    import constants as INQUIRIES
from app.corporate_access_resources.corporate_access_event_slots.models \
    import CorporateAccessEventSlot
from app.corporate_access_resources.corporate_access_event_slots.schemas \
    import (CorporateAccessEventSlotSchema,
            CorporateAccessEventSlotReadArgsSchema)
from app.corporate_access_resources.corporate_access_events.models import \
    CorporateAccessEvent
from app.corporate_access_resources.corporate_access_event_inquiries.\
    models import CorporateAccessEventInquiry

from queueapp.corporate_accesses.stats_tasks import (
    update_corporate_event_stats)
from queueapp.corporate_accesses.email_tasks import (
    send_corporate_access_event_slot_time_change_email)
from queueapp.corporate_accesses.email_tasks import (
    send_corporate_access_event_slot_updated_email)
from queueapp.corporate_accesses.email_tasks import (
    send_corporate_access_event_slot_deleted_email)


class CorporateAccessEventSlotAPI(AuthResource):
    """
    CRUD API for managing corporate access event slots
    """

    @swag_from('swagger_docs/corporate_access_event_slots_post.yml')
    def post(self):
        """
        Create a corporate access event slot
        """
        corp_access_event_slot_schema = CorporateAccessEventSlotSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            collaborator_ids = []
            # validate and deserialize input into object
            data, errors = corp_access_event_slot_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            event_data = CorporateAccessEvent.query.get(data.event_id)
            collaborator_ids = [col.collaborator_id
                                for col in event_data.collaborators]
            # for group account type user check with account id for
            # child account
            if ((event_data.created_by != g.current_user['row_id'] or
                    event_data.account_id != g.current_user['account_id'])and
                    g.current_user['row_id'] not in collaborator_ids):
                c_abort(403)
            # for cancelled event
            if event_data.cancelled:
                c_abort(422, message='Corporate Access Event cancelled,'
                        ' so you cannot add a slot')
            # if event is non has_slot, so can not add slots in
            # particular event
            if not event_data.event_sub_type.has_slots:
                c_abort(422, errors={
                    'slots': ['Event sub type is not has_slot, '
                              'so you can not add slots']})
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            data.account_id = g.current_user['account_id']
            db.session.add(data)
            db.session.commit()
            update_corporate_event_stats.s(
                True, data.event_id).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (event_id)=(10) is not present in
                # table "corporate_access_event".
                # Key (account_id)=(4) is not present in table "account".
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

        return {'message': 'Corporate Access Event Slot added: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201

    @swag_from('swagger_docs/corporate_access_event_slots_put.yml')
    def put(self, row_id):
        """
        Update a corporate access event slot
        """
        corp_access_event_slot_schema = CorporateAccessEventSlotSchema()
        # first find model
        model = None
        collaborator_ids = None
        try:
            model = CorporateAccessEventSlot.query.get(row_id)
            if model is None:
                c_abort(404, message='Corporate Access Event Slot id: %s'
                        ' does not exist' % str(row_id))
            # old_corporate_access_event_id, to be used for stats calculation
            ce_id = model.event_id
            # old started_at and ended_at, to be used for informing inquirers,
            # collaborators and creators in case of change in timings via email
            old_started_at = model.started_at
            old_ended_at = model.ended_at
            # old_address, to be used for informing inquirers, collaborators
            # and creators in case of change in venue via emails
            old_address = model.address
            event_data = CorporateAccessEvent.query.get(model.event_id)
            collaborator_ids = [col.collaborator_id
                                for col in event_data.collaborators]
            # only collaborators and creator can change slot
            # for group account type user check with account id for
            # child account
            if ((event_data.created_by != g.current_user['row_id'] or
                    event_data.account_id != g.current_user['account_id']) and
                    g.current_user['row_id'] not in collaborator_ids and
                    model.created_by != g.current_user['row_id']):
                c_abort(403)

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
            data, errors = corp_access_event_slot_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # for cancelled event
            event = CorporateAccessEvent.query.get(model.event_id)
            if event.cancelled:
                c_abort(422, message='Corporate Access Event cancelled,'
                        ' so you cannot update a slot')
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()
            # old_corporate_access_event_id, to be used for stats calculation
            if ce_id != model.event_id:
                update_corporate_event_stats.s(True, ce_id).delay()
            update_corporate_event_stats.s(True, model.event_id).delay()
            # #TODO: removed but maybe needed
            # # if timings changed, send emails
            # if old_started_at != model.started_at or\
            #         old_ended_at != model.ended_at:
            #     send_corporate_access_event_slot_time_change_email.s(
            #         True, model.row_id, ce_id).delay()
            # if slot details changed, send emails
            if old_address != model.address or\
                    old_started_at != model.started_at or\
                    old_ended_at != model.ended_at:
                # #TODO: Enhancements to be made for address
                send_corporate_access_event_slot_updated_email.s(
                    True, model.row_id, ce_id).delay()

        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (event_id)=(10) is not present in
                # table "corporate_access_event".
                # Key (account_id)=(4) is not present in table "account".
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
        return {'message': 'Updated Corporate Access Event Slot id: %s' %
                str(row_id)}, 200

    @swag_from('swagger_docs/corporate_access_event_slots_delete.yml')
    def delete(self, row_id):
        """
        Delete a corporate access event slot
        """
        model = None
        try:
            # first find model
            collaborator_ids = None
            model = CorporateAccessEventSlot.query.get(row_id)
            if model is None:
                c_abort(404, message='Corporate Access Event Slot id: %s'
                        ' does not exist' % str(row_id))

            # old_corporate_access_event_id, to be used for stats calculation
            ce_id = model.event_id
            event_data = CorporateAccessEvent.query.get(ce_id)

            # collaborators details
            collaborator_ids = [col.collaborator_id
                                for col in event_data.collaborators]
            # only collaborators and creator can delete slot
            # for group account type user check with account id for
            # child account
            if ((event_data.created_by != g.current_user['row_id'] or
                    event_data.account_id != g.current_user['account_id']) and
                    g.current_user['row_id'] not in collaborator_ids and
                    model.created_by != g.current_user['row_id']):
                c_abort(403)
            # for cancelled event
            if event_data.cancelled:
                c_abort(422, message='Corporate Access Event cancelled,'
                        ' so you cannot delete a slot')

            # #TODO: needed to be discussed
            # # creator details
            # creator_email = event_data.creator.email
            # creator_name = event_data.creator.profile.first_name

            # # slot inquirers details
            # slot_inquirers = CorporateAccessEventInquiry.query.filter_by(
            #     corporate_access_event_id=ce_id,
            #     corporate_access_event_slot_id=row_id,
            #     status=INQUIRIES.CONFIRMED).all()
            # slot_inquirer_user_ids = [si.created_by for si in slot_inquirers]

            # # send emails
            # send_corporate_access_event_slot_deleted_email.s(
            #     True, creator_email, creator_name,
            #     collaborator_ids, slot_inquirer_user_ids,
            #     event_data.created_by).delay()

            db.session.delete(model)
            db.session.commit()
            # calculate stats
            update_corporate_event_stats.s(True, ce_id).delay()

        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204

    @swag_from('swagger_docs/corporate_access_event_slots_get.yml')
    def get(self, row_id):
        """
        Get a corporate access event slot by id
        """
        corp_access_event_slot_schema = CorporateAccessEventSlotSchema()
        model = None
        try:
            # first find model
            model = CorporateAccessEventSlot.query.get(row_id)
            if model is None:
                c_abort(404, message='Corporate Access Event Slot id: %s'
                        ' does not exist' % str(row_id))
            result = corp_access_event_slot_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class CorporateAccessEventSlotListAPI(AuthResource):
    """
    Read API for corporate access event slot list,
    i.e, more than 1 corporate access event slot
    """
    model_class = CorporateAccessEventSlot

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['corporate_access_event',
                                    'account', 'creator']
        super(CorporateAccessEventSlotListAPI, self).__init__(*args, **kwargs)

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
        # query = query.options(joinedload(CorporateAccessEventSlot.))
        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/corporate_access_event_slots_get_list.yml')
    def get(self):
        """
        Get the list
        """
        corp_access_event_slot_read_schema = \
            CorporateAccessEventSlotReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            corp_access_event_slot_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(CorporateAccessEventSlot),
                                 operator)
            # making a copy of the main output schema
            corp_access_event_slot_schema = CorporateAccessEventSlotSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                corp_access_event_slot_schema = CorporateAccessEventSlotSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching corporate'
                        ' access event slots found')
            result = corp_access_event_slot_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
