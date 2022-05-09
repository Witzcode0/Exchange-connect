"""
API endpoints for "corporate access event attendees" package.
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
from app.corporate_access_resources.corporate_access_event_attendees.models \
    import CorporateAccessEventAttendee
from app.corporate_access_resources.corporate_access_event_attendees.schemas \
    import (CorporateAccessEventAttendeeSchema,
            CorporateAccessEventAttendeeEditSchema,
            CorporateAccessEventAttendeeReadArgsSchema,
            BulkCorporateAccessAttendeesSchema)
from app.corporate_access_resources.corporate_access_events.models import \
    CorporateAccessEvent
from app.corporate_access_resources.corporate_access_event_invitees.\
    models import CorporateAccessEventInvitee
from app.corporate_access_resources.corporate_access_event_inquiries.models \
    import CorporateAccessEventInquiry

from queueapp.corporate_accesses.stats_tasks import (
    update_corporate_event_stats)


class CorporateAccessEventAttendeeAPI(AuthResource):
    """
    CRUD API for managing corporate access event attendee
    """
    @swag_from('swagger_docs/corporate_access_event_attendees_post.yml')
    def post(self):
        """
        Create a corporate access event attendee
        """
        corporate_access_event_attendees_schema = \
            CorporateAccessEventAttendeeSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            collaborator_ids = None
            data, errors = corporate_access_event_attendees_schema.load(
                json_data)
            if errors:
                c_abort(422, errors=errors)
            # only event creator and collaborator have access
            # for create attendee
            event_data = CorporateAccessEvent.query.get(
                data.corporate_access_event_id)
            collaborator_ids = [col.collaborator_id
                                for col in event_data.collaborators]
            if (g.current_user['row_id'] not in collaborator_ids and
                    event_data.created_by != g.current_user['row_id']):
                c_abort(403)
            # for cancelled cae
            cae = CorporateAccessEvent.query.get(data.corporate_access_event_id)
            if cae.cancelled:
                c_abort(422, message='Corporate Access Event cancelled,'
                        'so you cannot add attendees')
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()
            update_corporate_event_stats.s(
                True, data.corporate_access_event_id).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (corporate_access_event_id, attendee_id, /
                # corporate_access_event_slot_id)=(1, 1, 3) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (corporate_access_event_id)=(12) is not present in  \
                # table "corporate_access_event".
                # Key (attendee_id)=(15) is not present in table "user".
                # Key (corporate_access_event_slot_id)=(13) is not
                # present in table "corporate_access_event_slot".
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

        return {'message': 'Corporate access event attendee added: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201

    @swag_from('swagger_docs/corporate_access_event_attendees_put.yml')
    def put(self, row_id):
        """
        Update a corporate access event attendee
        """
        corporate_access_event_attendees_edit_schema = \
            CorporateAccessEventAttendeeEditSchema()
        # first find model
        model = None
        try:
            model = CorporateAccessEventAttendee.query.get(row_id)
            if model is None:
                c_abort(404, message='Corporate access event Attendee id: %s'
                        'does not exist' % str(row_id))
            #model.corporate_access_event_id
            is_cancelled = CorporateAccessEvent.query.get(
                                model.corporate_access_event_id)

            # only event creator and collaborator have access
            # for update attendee
            event_data = CorporateAccessEvent.query.get(
                model.corporate_access_event_id)
            if event_data.cancelled is True:
                c_abort(422, message='Corporate access event is cancelled'
                                     'you cannot update rating!')
            collaborator_ids = [col.collaborator_id
                                for col in event_data.collaborators]
            if (g.current_user[
                    'row_id'] not in collaborator_ids and
                    event_data.created_by != g.current_user['row_id'] and
                    g.current_user['row_id'] != model.attendee_id and
                    model.invitee_id and
                    g.current_user['email'] !=
                    model.guest_invitee.invitee_email):
                c_abort(403)
            # old_corporate_access_event_id, to be used for stats calculation
            ce_id = model.corporate_access_event_id
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
            # event creator and collaborator can to give rating
            if ('rating' in json_data and json_data['rating'] and
                    g.current_user['row_id'] != model.attendee_id and
                    model.invitee_id and
                    g.current_user['email'] !=
                    model.guest_invitee.invitee_email):
                json_data.pop('rating')
            # attendee can not give comment
            if ('comment' in json_data and json_data['comment'] and
                    g.current_user['row_id'] == model.attendee_id or
                    (model.invitee_id and
                        g.current_user['email'] ==
                        model.guest_invitee.invitee_email)):
                json_data.pop('comment')
            data, errors = corporate_access_event_attendees_edit_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # for cancelled cae
            cae = CorporateAccessEvent.query.get(model.corporate_access_event_id)
            if cae.cancelled:
                c_abort(422, message='Corporate Access Event cancelled,'
                        'so you cannot update attendees')
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()
            update_corporate_event_stats.s(True, ce_id).delay()
            # old_corporate_access_event_id, to be used for stats calculation
            if ce_id != model.corporate_access_event_id:
                update_corporate_event_stats.s(
                    True, model.corporate_access_event_id).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (corporate_access_event_id, attendee_id, /
                # corporate_access_event_slot_id)=(1, 1, 3) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (corporate_access_event_id)=(12) is not present in  \
                # table "corporate_access_event".
                # Key (attendee_id)=(15) is not present in table "user".
                # Key (corporate_access_event_slot_id)=(13) is not
                # present in table "corporate_access_event_slot".
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
        return {'message': 'Updated Corporate access event Attendee id: %s' %
                str(row_id)}, 200

    @swag_from('swagger_docs/corporate_access_event_attendees_delete.yml')
    def delete(self, row_id):
        """
        Delete a corporate access event attendee
        """
        model = None
        try:
            # first find model
            model = CorporateAccessEventAttendee.query.get(row_id)
            if model is None:
                c_abort(404, message='Corporate access event Attendee id: %s'
                        'does not exist' % str(row_id))
            # only event creator and collaborator have access
            # for delete attendee
            event_data = CorporateAccessEvent.query.get(
                model.corporate_access_event_id)
            collaborator_ids = [col.collaborator_id
                                for col in event_data.collaborators]

            if (g.current_user[
                    'row_id'] not in collaborator_ids and
                    event_data.created_by != g.current_user['row_id']):
                c_abort(403)
            # old_corporate_access_event_id, to be used for stats calculation
            ce_id = model.corporate_access_event_id
            # for cancelled cae
            cae = CorporateAccessEvent.query.get(ce_id)
            if cae.cancelled:
                c_abort(422, message='Corporate Access Event cancelled,'
                        'so you cannot delete attendees')
            db.session.delete(model)
            db.session.commit()
            # old_corporate_access_event_id, to be used for stats calculation
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

    @swag_from('swagger_docs/corporate_access_event_attendees_get.yml')
    def get(self, row_id):
        """
        Get a corporate access event attendee by id
        """
        corporate_access_event_attendees_schema = \
            CorporateAccessEventAttendeeSchema()
        model = None
        try:
            # first find model
            model = CorporateAccessEventAttendee.query.get(row_id)
            if model is None:
                c_abort(404, message='Corporate access event Attendee id: %s'
                        'does not exist' % str(row_id))
            result = corporate_access_event_attendees_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class CorporateAccessEventAttendeeListAPI(AuthResource):
    """
    Read API for corporate access event attendee lists,
    i.e, more than 1 attendee
    """
    model_class = CorporateAccessEventAttendee

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['attendee', 'corporate_access_event_slot',
                                    'corporate_access_event']
        super(CorporateAccessEventAttendeeListAPI, self).__init__(
            *args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        cancelled = filters.pop('cancelled', None)

        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)
        # build specific extra queries filters
        if extra_query:
            pass
        # all attended list attend by current user
        query_filters['base'].append(
            CorporateAccessEventAttendee.attendee_id ==
            g.current_user['row_id'])
        query = self._build_final_query(query_filters, query_session, operator)

        query = query.join(CorporateAccessEvent, CorporateAccessEvent.row_id == CorporateAccessEventAttendee.corporate_access_event_id )

        if cancelled == False:
            query = query.filter(CorporateAccessEvent.cancelled.is_(False))

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/corporate_access_event_attendees_get_list.yml')
    def get(self):
        """
        Get the list
        """
        corp_event_attendees_read_schema = \
            CorporateAccessEventAttendeeReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            corp_event_attendees_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(
                                     CorporateAccessEventAttendee), operator)
            # making a copy of the main output schema
            corp_attendees_schema = CorporateAccessEventAttendeeSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                corp_attendees_schema = CorporateAccessEventAttendeeSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(
                    404, message='No matching Corporate access event'
                    ' attendee found')
            result = corp_attendees_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class BulkCorporateAccessEventAttendeeAPI(AuthResource):
    """
    API for attended in bulk post, put and delete
    """

    @swag_from('swagger_docs/corporate_access_event_bulk_attendees.yml')
    def post(self):
        """
        Create, change and delete in bulk corporate access event attendee
        """
        bulk_corp_event_attendees_schema = BulkCorporateAccessAttendeesSchema()
        attn_schema = CorporateAccessEventAttendeeSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            data, errors = bulk_corp_event_attendees_schema.load(json_data)

            if errors:
                c_abort(422, errors=errors)
            # only event creator and collaborator have access
            # for create attendee
            event_data = CorporateAccessEvent.query.get(
                data['corporate_access_event_id'])
            collaborator_ids = [col.collaborator_id
                                for col in event_data.collaborators]
            if (g.current_user['row_id'] not in collaborator_ids and
                    event_data.created_by != g.current_user['row_id']):
                c_abort(403)
            # create and change attended
            if 'attendees' in data and data['attendees']:
                for attn in data['attendees']:
                    if 'inquiries' in attn:
                        for inq in attn['inquiries']:
                            # when row_id in inquiry so change attended
                            if 'rating' in inq:
                                inq.pop('rating')
                            if 'row_id' in inq:
                                atten_model = None
                                atten_model = CorporateAccessEventAttendee.\
                                    query.get(inq['row_id'])
                                if not atten_model:
                                    c_abort(
                                        404, message='Corporate access'
                                        ' event Attendee id: %s does not'
                                        ' exist' % str(inq['row_id']))
                                attn_data, errors = attn_schema.load(
                                    inq, instance=atten_model, partial=True)
                                if errors:
                                    db.session.rollback()
                                    c_abort(422, errors=errors)
                                attn_data.updated_by = g.current_user['row_id']
                                db.session.add(attn_data)
                            else:
                                # create new attended
                                if 'inquiry_id' in inq:
                                    inq_created = None
                                    inq_created = CorporateAccessEventInquiry.\
                                        query.filter_by(
                                            row_id=inq['inquiry_id']).first()
                                    if inq_created:
                                        inq['corporate_access_event_id'] = \
                                            data['corporate_access_event_id']
                                        inq['attendee_id'] = \
                                            inq_created.created_by
                                        inq['corporate_access_event_'
                                            'slot_id'] =\
                                            attn['corporate_access_event_'
                                                 'slot_id']
                                        inq_data, errors = attn_schema.load(
                                            inq)

                                        if errors:
                                            db.session.rollback()
                                            c_abort(422, errors=errors)

                                        db.session.add(inq_data)
                                        inq_data.created_by = g.current_user[
                                            'row_id']
                                        inq_data.updated_by = g.current_user[
                                            'row_id']
                        db.session.commit()
                    # this for direct add attended using invitee
                    if 'invitees' in attn:
                        for inv in attn['invitees']:
                            # when row_id in inquiry so change attended
                            if 'rating' in inv:
                                inq.pop('rating')
                            if 'row_id' in inv:
                                atten_model = None
                                atten_model = CorporateAccessEventAttendee.\
                                    query.get(inv['row_id'])
                                if not atten_model:
                                    c_abort(
                                        404, message='Corporate access event'
                                        ' Attendee id: %s does not exist' %
                                        str(inv['row_id']))
                                attn_data, errors = attn_schema.load(
                                    inv, instance=atten_model, partial=True)
                                if errors:
                                    db.session.rollback()
                                    c_abort(422, errors=errors)
                                attn_data.updated_by = g.current_user['row_id']
                                db.session.add(attn_data)
                            else:
                                # create new attended
                                invitee_data = None
                                if 'invitee_id' in inv:
                                    inv['corporate_access_event_id'] = \
                                        data['corporate_access_event_id']
                                    invitee_data =\
                                        CorporateAccessEventInvitee.query.get(
                                            inv['invitee_id'])
                                    if not invitee_data:
                                        db.session.rollback()
                                        c_abort(
                                            404, message='Corporate Access '
                                            'Event Invitee id: %s does not '
                                            'exist' % str(inv['invitee_id']))
                                    # if invitee_id hold not guest user
                                    if invitee_data.user_id:
                                        inv['attendee_id'] = invitee_data.\
                                            user_id
                                        inv.pop('invitee_id')
                                    inv_data, errors = attn_schema.load(
                                        inv)
                                    if errors:
                                        db.session.rollback()
                                        c_abort(422, errors=errors)

                                    db.session.add(inv_data)
                                    inv_data.created_by = g.current_user[
                                        'row_id']
                                    inv_data.updated_by = g.current_user[
                                        'row_id']
                        db.session.commit()
            # delete attended by row_ids
            if 'attendee_delete_ids' in data and data['attendee_delete_ids']:
                CorporateAccessEventAttendee.query.filter(
                    CorporateAccessEventAttendee.row_id.in_(
                        data['attendee_delete_ids'])).delete(
                    synchronize_session=False)
                db.session.commit()
            update_corporate_event_stats.s(
                True, data['corporate_access_event_id']).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (corporate_access_event_id, attendee_id, /
                # corporate_access_event_slot_id)=(1, 1, 3) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (corporate_access_event_id)=(12) is not present in  \
                # table "corporate_access_event".
                # Key (attendee_id)=(15) is not present in table "user".
                # Key (corporate_access_event_slot_id)=(13) is not
                # present in table "corporate_access_event_slot".
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

        return {'message': 'Corporate access event attendee added'}, 201
