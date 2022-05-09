"""
Helper fields for models
"""

from flask import current_app
from sqlalchemy import types, cast


class LCString(types.TypeDecorator):
    """
    Lower case string, converts the value to lowercase before entering db.
    """

    impl = types.String

    def process_bind_param(self, value, dialect):
        try:
            if value:
                value = value.lower()
        except Exception as e:
            current_app.logger.exception(e)
        return value


class UCString(types.TypeDecorator):
    """
    Upper case string, converts the value to uppercase before entering db.
    """

    impl = types.String

    def process_bind_param(self, value, dialect):
        try:
            if value:
                value = value.upper()
        except Exception as e:
            current_app.logger.exception(e)
        return value


class ChoiceString(types.TypeDecorator):
    """
    Alternative to Enum type, allows validation of choices, but keeps in db as
    string instead of enum, useful for easy future modifications.
    """

    impl = types.String

    def __init__(self, choices, matching='exact', nullable=True, **kw):
        """
        Initialize the column.

        :param choices:
            the choices list of tuples
        :param matching:
            the matching type during queries, valid values are 'exact'|'like'
        :param nullable:
            is this nullable, for easy binding, and value generation
        """
        self.choices = dict(choices)
        self.matching = matching
        self.nullable = nullable
        super(ChoiceString, self).__init__(**kw)

    def process_bind_param(self, value, dialect):
        if value is None and self.nullable:
            return None
        return [k for k, v in self.choices.items() if v == value][0]

    def process_result_value(self, value, dialect):
        if value is None and self.nullable:
            return None
        return self.choices[value]


class CastingArray(types.ARRAY):

    def bind_expression(self, bindvalue):
        return cast(bindvalue, self)
