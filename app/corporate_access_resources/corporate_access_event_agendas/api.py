"""
API endpoints for "corporate access event agendas" package.
"""

from werkzeug.exceptions import HTTPException, Forbidden
from flask import current_app
from flask_restful import abort
from sqlalchemy.orm import load_only
from flasgger.utils import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.corporate_access_resources.corporate_access_event_agendas.models \
    import CorporateAccessEventAgenda
from app.corporate_access_resources.corporate_access_events.models \
    import CorporateAccessEvent
from app.corporate_access_resources.corporate_access_event_agendas.schemas \
    import (CorporateAccessEventAgendaSchema,
            CorporateAccessEventAgendaReadArgsSchema)

from queueapp.corporate_accesses.stats_tasks import (
    update_corporate_event_stats)


class CorporateAccessEventAgendaAPI(AuthResource):
    """
    CRUD API for managing corporate access event agenda
    """
    @swag_from('swagger_docs/corporate_access_event_agenda_delete.yml')
    def delete(self, row_id):
        """
        Delete a corporate access event agenda
        """
        model = None
        try:
            # first find model
            model = CorporateAccessEventAgenda.query.get(row_id)
            if model is None:
                c_abort(404, message='Corporate Access Event Agenda id: %s'
                        ' does not exist' % str(row_id))
            # old_corporate_access_event_id, to be used for stats calculation
            ce_id = model.corporate_access_event_id
            # for cancelled cae
            cae = CorporateAccessEvent.query.get(ce_id)
            if cae.cancelled:
                c_abort(422, message='Corporate Access Event cancelled,'
                        'so you cannot delete agendas')
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


class CorporateAccessEventAgendaListAPI(AuthResource):
    """
    Read API for corporate access event agenda list,
    i.e, more than 1 corporate access event host
    """
    model_class = CorporateAccessEventAgenda

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['corporate_access_event']
        super(CorporateAccessEventAgendaListAPI, self).__init__(
            *args, **kwargs)

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

    @swag_from('swagger_docs/corporate_access_event_agenda_get_list.yml')
    def get(self):
        """
        Get the list
        """
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            CorporateAccessEventAgendaReadArgsSchema())
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(CorporateAccessEventAgenda),
                                 operator)
            # making a copy of the main output schema
            corp_access_event_agenda_schema = \
                CorporateAccessEventAgendaSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                corp_access_event_agenda_schema = \
                    CorporateAccessEventAgendaSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching corporate'
                        ' access event agenda found')
            result = corp_access_event_agenda_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
