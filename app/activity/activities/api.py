"""
API endpoints for "activities" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import load_only, joinedload
from sqlalchemy import and_, any_, func, or_
    
from app.base import constants as APP
from app import db, c_abort
from app.base.api import AuthResource
from app.common.helpers import store_file, delete_files
from app.resources.contacts.models import Contact
from app.activity.activities.models import Activity
from app.activity.activities.schemas import (
    ActivitySchema, ActivityReadArgsSchema)
from app.resources.activity_type.models import ActivityType
from app.common.helpers import time_converter

from queueapp.activity_tasks import manage_activity_reminder
from queueapp.goaltracker_tasks import manage_related_goaltrackers
from app.activity.activities_institution.models import ActivityInstitution, ActivityInstitutionParticipant
from app.activity.activities_institution.schemas import ActivityInstitutionSchema, ActivityInstitutionParticipantSchema
from app.activity.activities_organiser.models import ActivityOrganiser, ActivityOrganiserParticipant
from app.activity.activities_organiser.schemas import ActivityOrganiserSchema, ActivityOrganiserParticipantSchema
from app.activity.activities_representative.models import ActivityRepresentative
from app.activity.activities_representative.schemas import ActivityRepresentativeSchema
from app.resources.goaltrackers.models import GoalTracker
from app.resources.goaltrackers.helpers import goal_count_update

# schema for reading get arguments
activity_read_schema = ActivityReadArgsSchema(strict=True)


class ActivityAPI(AuthResource):
    """
    Create, update, delete API for activities
    """

    def post(self):
        """
        Create an activity
        """
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            return {'message': 'No input data provided'}, 400

        try:
            # validate and deserialize input into object
            activity_schema = ActivitySchema()
            data, errors = activity_schema.load(json_data)
            if errors:
                return errors, 422

            # no errors, so add data to db
            # manage relations/foreign keys
            data.created_by = g.current_user['row_id']
            db.session.add(data)
            # db.session.commit()

            # manage goal counter
            results = GoalTracker.query.filter_by(created_by=g.current_user['row_id'],
                                                  activity_type=data.activity_type).all()

            for goal in results:
                goal.goal_count, goal.completed_activity_ids = goal_count_update(goal)
                db.session.add(goal)

            db.session.commit()

            # manage files
            if activity_schema._cached_files or 'file_ids' in json_data:
                for cf in activity_schema._cached_files:
                    if cf not in data.files:
                        data.files.append(cf)
                db.session.commit()

            # manage participants list
            if activity_schema._cached_contacts:
                for cp in activity_schema._cached_contacts:
                    if cp not in data.participants:
                        data.participants.append(cp)
            if 'institution_parts' in json_data and json_data['institution_parts']:
                for part in json_data['institution_parts']:
                    parts_json_data = part
                    parts_json_data['activity_id'] = data.row_id
                    data1, errors = ActivityInstitutionParticipantSchema().load(parts_json_data)
                    if errors:
                        return errors,422
                    db.session.add(data1)
            if 'institution_info' in json_data and json_data['institution_info']:
                ins_json_data = json_data['institution_info']
                ins_json_data['activity_id'] = data.row_id
                data2, errors = ActivityInstitutionSchema().load(ins_json_data)
                if errors:
                    return errors,422
                db.session.add(data2)
            if 'organiser_parts' in json_data and json_data['organiser_parts']:
                for part in json_data['organiser_parts']:
                    parts_json_data = part
                    parts_json_data['activity_id'] = data.row_id
                    data3, errors = ActivityOrganiserParticipantSchema().load(parts_json_data)
                    if errors:
                        return errors,422
                    db.session.add(data3)
            if 'organiser_info' in json_data and json_data['organiser_info']:
                org_json_data = json_data['organiser_info']
                org_json_data['activity_id'] = data.row_id
                data4, errors = ActivityOrganiserSchema().load(org_json_data)
                if errors:
                    return errors,422
                db.session.add(data4)
            if 'representatives_list' in json_data and json_data['representatives_list']:
                for part in json_data['representatives_list']:
                    parts_json_data = part
                    parts_json_data['activity_id'] = data.row_id
                    data5, errors = ActivityRepresentativeSchema().load(parts_json_data)
                    if errors:
                        return errors,422
                    db.session.add(data5) 

            db.session.commit()



            manage_activity_reminder.s(True, data.row_id).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
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

        return {'message': 'Activity Added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    def put(self, row_id):
        """
        Update an activity, either pass file data as multipart-form,
        or json data
        """
        # first find model
        model = None
        try:
            model = Activity.query.get(row_id)
            if model is None or model.deleted:
                return {
                    'message': 'Activity id: %s does not exist' %
                    str(row_id)}, 404
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
        except Forbidden as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            return {}, 500

        json_data = {}
        org_started_at = model.started_at
        org_type = model.activity_type

        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            return {'message': 'No input data provided'}, 400

        try:
            activity_schema = ActivitySchema()

            # validate and deserialize input
            data, errors = activity_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)

            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()

            # manage goal count
            results = GoalTracker.query.filter_by(created_by=g.current_user['row_id']).all()

            for goal in results:
                goal.goal_count, goal.completed_activity_ids = goal_count_update(goal)
                db.session.add(goal)

            db.session.commit()

            # manage event files
            if activity_schema._cached_files or 'file_ids' in json_data:
                # add new ones
                for cf in activity_schema._cached_files:
                    if cf not in data.files:
                        data.files.append(cf)
                # remove old ones
                for oldcf in data.files[:]:
                    if oldcf not in activity_schema._cached_files:
                        data.files.remove(oldcf)
                db.session.commit()
            # manage participants list

            if 'institution_parts' in json_data:
                lis_ins = []
                for part in json_data['institution_parts']:
                    participant_name = None
                    user_id = None
                    people_id = None
                    contact_id = None
                    if 'participant_name' in part:
                        participant_name = part['participant_name']
                    if 'user_id' in part:
                        user_id = part['user_id']
                    if 'people_id' in part:
                        people_id = part['people_id']
                    if 'contact_id' in part:
                        contact_id = part['contact_id']
                    institutes = ActivityInstitutionParticipant.query.filter(
                        ActivityInstitutionParticipant.activity_id == row_id,
                        ActivityInstitutionParticipant.participant_name == participant_name,
                        ActivityInstitutionParticipant.user_id == user_id,
                        ActivityInstitutionParticipant.people_id == people_id,
                        ActivityInstitutionParticipant.contact_id == contact_id).all()
                    if institutes:
                        for inst in institutes:
                            if inst.row_id not in lis_ins:
                                lis_ins.append(inst.row_id)
                    else:
                        part['activity_id'] = row_id
                        ins_part_data, errors = ActivityInstitutionParticipantSchema().load(part)
                        if errors:
                            return errors, 422
                        db.session.add(ins_part_data)
                        db.session.commit()
                        lis_ins.append(ins_part_data.row_id)
                for oldcp in data.institution_participants:
                    if oldcp.row_id not in lis_ins:
                        db.session.delete(oldcp)
                        db.session.commit()
            if 'institution_info' in json_data:
                if json_data['institution_info']:
                    institution_dic = json_data['institution_info'].copy()
                    lis_ins = []
                    # for part in json_data['institution_parts']:
                    account_name = None
                    account_id = None
                    factset_entity_id = None
                    if 'account_name' in json_data['institution_parts']:
                        account_name = json_data['institution_parts']['account_name']
                    if 'account_id' in json_data['institution_parts']:
                        account_id = json_data['institution_parts']['account_id']
                    if 'factset_entity_id' in json_data['institution_parts']:
                        factset_entity_id = json_data['institution_parts']['factset_entity_id']
                    institute = ActivityInstitution.query.filter(
                        ActivityInstitution.activity_id == row_id,
                        ActivityInstitution.account_name == account_name,
                        ActivityInstitution.account_id == account_id,
                        ActivityInstitution.factset_entity_id == factset_entity_id).first()
                    if institute:
                        lis_ins.append(inst.row_id)
                    else:
                        institution_dic['activity_id'] = row_id
                        ins_data, errors = ActivityInstitutionSchema().load(institution_dic)
                        if errors:
                            return errors, 422
                        db.session.add(ins_data)
                        db.session.commit()
                        lis_ins.append(ins_data.row_id)
                    for oldcp in data.institution:
                        if oldcp.row_id not in lis_ins:
                            db.session.delete(oldcp)
                            db.session.commit()
                else:
                    for oldcp in data.institution:
                        db.session.delete(oldcp)
                        db.session.commit()
            if 'organiser_parts' in json_data:
                lis_org = []
                for part in json_data['organiser_parts']:
                    participant_name = None
                    user_id = None
                    contact_id = None
                    if 'contact_id' in part:
                        contact_id = part['contact_id']
                    if 'participant_name' in part:
                        participant_name = part['participant_name']
                    if 'user_id' in part:
                        user_id = part['user_id']
                    orgs = ActivityOrganiserParticipant.query.filter(
                        ActivityOrganiserParticipant.activity_id == row_id,
                        ActivityOrganiserParticipant.participant_name == participant_name,
                        ActivityOrganiserParticipant.user_id == user_id,
                        ActivityOrganiserParticipant.contact_id == contact_id).all()
                    if orgs:
                        for org in orgs:
                            if org.row_id not in lis_org:
                                lis_org.append(org.row_id)
                    else:
                        part['activity_id'] = row_id
                        org_part_data, errors = ActivityOrganiserParticipantSchema().load(part)
                        if errors:
                            return errors, 422
                        db.session.add(org_part_data)
                        db.session.commit()
                        lis_org.append(org_part_data.row_id)
                for oldcp in data.organiser_participants:
                    if oldcp.row_id not in lis_org:
                        db.session.delete(oldcp)
                        db.session.commit()
            if 'organiser_info' in json_data:
                if json_data['organiser_info']:
                    org_dic = json_data['organiser_info'].copy()
                    lis_org = []
                    # for part in json_data['institution_parts']:
                    account_name = None
                    account_id = None
                    if 'account_name' in json_data['organiser_info']:
                        account_name = json_data['organiser_info']['account_name']
                    if 'account_id' in json_data['organiser_info']:
                        account_id = json_data['organiser_info']['account_id']
                    org = ActivityOrganiser.query.filter(
                        ActivityOrganiser.activity_id == row_id,
                        ActivityOrganiser.account_name == account_name,
                        ActivityOrganiser.account_id == account_id).first()
                    if org:
                        lis_org.append(org.row_id)
                    else:
                        org_dic['activity_id'] = row_id
                        org_part, errors = ActivityOrganiserSchema().load(org_dic)
                        if errors:
                            return errors, 422
                        db.session.add(org_part)
                        db.session.commit()
                        lis_org.append(org_part.row_id)
                    for oldcp in data.organiser:
                        if oldcp.row_id not in lis_org:
                            db.session.delete(oldcp)
                            db.session.commit()
                else:
                    for oldcp in data.organiser:
                        db.session.delete(oldcp)
                        db.session.commit()

            if 'representatives_list' in json_data:
                lis_rep = []
                for part in json_data['representatives_list']:
                    user_id = None
                    contact_id = None
                    user_name = None
                    if 'user_id' in part:
                        user_id = part['user_id']
                    if 'contact_id' in part:
                        contact_id = part['contact_id']
                    if 'user_name' in part:
                        user_name = part['user_name']
                    representatives = ActivityRepresentative.query.filter(
                        ActivityRepresentative.activity_id == row_id,
                        ActivityRepresentative.user_id == user_id,
                        ActivityRepresentative.contact_id == contact_id,
                        ActivityRepresentative.user_name == user_name,).all()
                    if representatives:
                        for reps in representatives:
                            if reps.row_id not in lis_rep:
                                lis_rep.append(reps.row_id)
                    else:
                        part['activity_id'] = row_id
                        rep_data, errors = ActivityRepresentativeSchema().load(part)
                        if errors:
                            return errors, 422
                        db.session.add(rep_data)
                        db.session.commit()
                        lis_rep.append(rep_data.row_id)
                        # db.session.commit()
                for oldcp in data.representatives:
                    if oldcp.row_id not in lis_rep:
                        db.session.delete(oldcp)
                db.session.commit()  

            if (activity_schema._cached_contacts or
                    'invitee_ids' in json_data):
                # add new ones
                for cp in activity_schema._cached_contacts:
                    if cp not in data.participants:
                        data.participants.append(cp)
                # remove old ones
                for oldcp in data.participants[:]:
                    if oldcp not in activity_schema._cached_contacts:
                        data.participants.remove(oldcp)
            # manage users (assignee) list
            # if activity_schema._cached_crm_contacts or 'crm_participant_ids' in json_data:
            #     # add new ones
            #     for cu in activity_schema._cached_crm_contacts:
            #         if cu not in data.crm_participants:
            #             data.crm_participants.append(cu)
            #     # remove old ones
            #     for oldcu in data.crm_participants[:]:
            #         if oldcu not in activity_schema._cached_crm_contacts:
            #             data.crm_participants.remove(oldcu)
            db.session.add(data)
            db.session.commit()
            manage_activity_reminder.s(True, data.row_id).delay()
            # manage goal tracker (goal count, completed ids) list
            manage_related_goaltrackers.s(
                True, data.row_id, org_started_at, org_type).delay()
        except IntegrityError as e:
            # format of the message:
            # Key (contact_id)=(17) is not present in table "contact".
            column = e.orig.diag.message_detail.split('(')[1][:-2]
            cvalue = e.orig.diag.message_detail.split('=')[1].split(
                '(')[1].split(')')[0]
            db.session.rollback()
            return {column: '%s does not exist' % cvalue}, 422
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            return {}, 500
        else:
            message = 'Updated Activity id: %s' % str(row_id)
        return {'message': message}, 200

    def delete(self, row_id):
        """
        Delete an activity
        """
        model = None
        completed_ids_dict = {}
        try:
            # first find model
            model = Activity.query.get(row_id)
            if model is None or model.deleted:
                return {
                    'message': 'Activity id: %s does not exist' %
                    str(row_id)}, 404
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            # if model is found, and not yet deleted, delete it
            model.deleted = True
            db.session.add(model)
            db.session.commit()

            #goal count
            results = GoalTracker.query.filter_by(created_by=g.current_user['row_id'], activity_type=model.activity_type).all()

            for goal in results:
                completed_ids = goal.completed_activity_ids
                if completed_ids:
                    for i in completed_ids:
                        if i == row_id:
                            completed_ids.remove(row_id)
                    completed_ids_dict[goal.row_id] = completed_ids
                for key, value in completed_ids_dict.items():
                    if goal.row_id == key:
                        goal.completed_activity_ids = None
                        db.session.commit()
                        goal.completed_activity_ids = value
                        goal.goal_count = len(completed_ids)
                db.session.add(goal)
            db.session.commit()

        except Forbidden as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            return {}, 500
        return {}, 204

    def get(self, row_id):
        """
        Get an activity by id
        """
        model = None
        try:
            # first find model
            # TODO: optimise to load only certain attributes of contact, users?
            model = Activity.query.get(row_id)
            if model is None or model.deleted:
                return {
                    'message': 'Activity id: %s does not exist' %
                    str(row_id)}, 404
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            result = ActivitySchema(exclude=ActivitySchema._default_exclude_fields).dump(model)
        except Forbidden as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            return {}, 500

        return {'results': result}, 200


class ActivityList(AuthResource):
    """
    Read API for activity lists, i.e, more than 1 activity
    """
    model_class = Activity

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['participants', 'document_urls']
        super(ActivityList, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        account_name = filters.pop('account_name', None)
        agenda = filters.pop('agenda', None)
        flag = False
        flag2 = True
        flag5 = False

        # build the default queries, using the parent helper
        query_filters, extra_query, db_projection, s_projection, order, \
        paging = self._build_query(
            filters, pfields, sort, pagination, operator,
            include_deleted=include_deleted)
        mapper = inspect(Activity)

        # join outer
        innerjoin = False

        # build specific extra queries
        if extra_query:
            mapper = inspect(self.model_class)
            # for f in extra_query:
            if 'activity_name' in extra_query and extra_query['activity_name']:
                activity_name = '%' + (extra_query["activity_name"]).lower() + '%'
                query_filters['filters'].append(
                    func.lower(ActivityType.activity_name).like(activity_name))
            if "from_date" in extra_query and extra_query['from_date']:
                started_at = extra_query.pop('from_date')
                started_at = time_converter(started_at, 'UTC', 'Asia/Kolkata')
                started_at = started_at.strftime("%Y-%m-%dT%H:%M:%SZ")
                query_filters['filters'].append(Activity.started_at >= started_at)
            if "to_date" in extra_query and extra_query['to_date']:
                ended_to = extra_query.pop('to_date')
                ended_to = time_converter(ended_to, 'UTC', 'Asia/Kolkata')
                ended_to = ended_to.strftime("%Y-%m-%dT%H:%M:%SZ")
                query_filters['filters'].append(Activity.started_at <= ended_to)

        query_filters['base'].append(
            Activity.created_by == g.current_user['row_id'])

        # build specific extra queries
        query = self._build_final_query(query_filters, query_session, operator)

        query = query.join(
            ActivityType, ActivityType.row_id == Activity.activity_type)


        if account_name and agenda:
            query = query.filter(
                or_(func.lower(ActivityInstitution.account_name).like('%' + account_name.lower() + '%'),
                    func.lower(Activity.agenda).like('%' + agenda.lower() + '%')))
        else:
            flag5 = True
        if account_name:
            if flag5:
                query = query.filter(func.lower(ActivityInstitution.account_name).like(account_name.lower()))
            if flag2:
                if 'institution' not in sort['sort_by']:
                    query = query.join(ActivityInstitution, ActivityInstitution.activity_id == Activity.row_id, isouter=True)
                    flag2 = False
                else:
                    flag2 = False
            if flag2:
                if 'organiser' not in sort['sort_by']:
                    query = query.join(ActivityInstitution, ActivityInstitution.activity_id == Activity.row_id, isouter=True)
            flag = True
            user_query = query
        if flag:
            final_query = user_query
        else:
            final_query = query

        if sort:
            for col in sort['sort_by']:
                if col == 'activity_name':
                    mapper = inspect(ActivityType)
                    col = 'activity_name'
                    sort_fxn = 'asc'
                    if sort['sort'] == 'dsc':
                        sort_fxn = 'desc'
                    order.append(getattr(mapper.columns[col], sort_fxn)())
                if col == 'institution':
                    final_query = query.join(ActivityInstitution, ActivityInstitution.activity_id == Activity.row_id, isouter=True)
                    mapper = inspect(ActivityInstitution)
                    col = 'account_name'
                    sort_fxn = 'asc'
                    if sort['sort'] == 'dsc':
                        sort_fxn = 'desc'
                    order.append(getattr(mapper.columns[col], sort_fxn)())
                if col == 'organiser':
                    final_query = query.join(ActivityOrganiser, ActivityOrganiser.activity_id == Activity.row_id,
                                             isouter=True)
                    mapper = inspect(ActivityOrganiser)
                    col = 'account_name'
                    sort_fxn = 'asc'
                    if sort['sort'] == 'dsc':
                        sort_fxn = 'desc'
                    order.append(getattr(mapper.columns[col], sort_fxn)())

        return final_query, db_projection, s_projection, order, paging

    def get(self):
        """
        Get the list
        """
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            activity_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Activity), operator)
            # making a copy of the main output schema
            activity_schema = ActivitySchema(exclude=ActivitySchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                activity_schema = ActivitySchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                return {'message': 'No matching activities found'}, 404
            result = activity_schema.dump(models, many=True)
        except Exception as e:
            current_app.logger.exception(e)
            return {}, 500
        return {'results': result.data, 'total': total}, 200
