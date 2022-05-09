from marshmallow import fields, validates_schema, ValidationError, validate
from app import ma
from app.global_search import constants as GS


class GlobalSearchSchema(ma.Schema):
    """
    Schema for global search
    """
    query = fields.String(load_only=True, required=True)
    page = fields.Integer(load_only=True, missing=1)
    per_page = fields.Integer(load_only=True, missing=20)
    main_filter = fields.String(
        load_only=True, missing=GS.ALL,
        validate=validate.OneOf(GS.GLOBAL_SEARCH_FILTERS))

    @validates_schema
    def validate_query(self, data):
        if 'query' in data and not data['query'].strip():
            raise ValidationError('query can not be blank', 'query')
