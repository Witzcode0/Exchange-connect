import dateutil
from flask import json
from flask_sqlalchemy import SQLAlchemy


# convert isoformat date string back to datetime object while loading
def object_hook(obj):
    _spec_type = obj.get('_spec_type')
    for k in obj:
        if 'time' in k or 'date' in k:
            try:
                obj[k] = dateutil.parser.parse(obj[k])
            except Exception as e:
                pass
    if not _spec_type:
        return obj

    """if _spec_type in CONVERTERS:
        return CONVERTERS[_spec_type](obj['val'])
    else:
        raise Exception('Unknown {}'.format(_spec_type))"""


def dateloads(obj):
    return json.loads(obj, object_hook=object_hook)


class HackSQLAlchemy(SQLAlchemy):
    """ Ugly way to get SQLAlchemy engine to pass the Flask JSON deserializer
    to `create_engine`.

    See https://github.com/mitsuhiko/flask-sqlalchemy/pull/67/files
    https://github.com/mitsuhiko/flask-sqlalchemy/issues/166

    """

    def apply_driver_hacks(self, app, info, options):
        options.update(json_deserializer=dateloads)
        super(HackSQLAlchemy, self).apply_driver_hacks(app, info, options)
