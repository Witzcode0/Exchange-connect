from werkzeug.exceptions import HTTPException
from flask_restful import abort
from flasgger.utils import swag_from

from app import c_abort
from app.base.api import AuthResource
from app.base import constants as APP
from app.global_search.helpers import query_index
from app.global_search.schemas import GlobalSearchSchema


class SearchAPI(AuthResource):
    """
    Global search api
    """

    def __init__(self, *args, **kwargs):
        super(SearchAPI, self).__init__(*args, **kwargs)

    @swag_from('swagger_docs/global_search_get.yml')
    def get(self):

        try:
            search_schema = GlobalSearchSchema(strict=True)

            filters, pfields, sort, pagination, operator = self.parse_args(
                search_schema)
            query = filters['query']
            page = pagination['page']
            per_page = pagination['per_page']
            main_filter = filters['main_filter']
            index = APP.DF_ES_INDEX
            result = query_index(index, query, main_filter, page, per_page)
            if result['total'] == 0:
                c_abort(404, message='No matching results found')

        except HTTPException as e:
            raise e
        except Exception as e:
            abort(500)
        return result