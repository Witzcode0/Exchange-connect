import datetime

from flask_script import Command, Option
from sqlalchemy import and_

from app import db
from app.survey_resources.surveys.models import Survey
from app.survey_resources.survey_responses.models import SurveyResponse
from app.survey_resources.surveys import constants as SURVEY


class CloseSurvey(Command):
    """
    Command to surveys closed by check end date of survey with current date

    :arg verbose:
        print progress
    :arg dry:
        dry run
    """

    option_list = [
        Option('--verbose', '-v', dest='verbose', action='store_true',
               default=False),
        Option('--dry', '-dry', dest='dry', action='store_true',
               default=False),
    ]

    def run(self, verbose, dry):
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')

        try:
            from_date = datetime.datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0) - \
                datetime.timedelta(days=2)
            to_date = datetime.datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0) - \
                datetime.timedelta(days=0)
            if not dry:
                Survey.query.filter(and_(
                    Survey.ended_at > from_date,
                    Survey.ended_at < to_date)).update(
                    {Survey.status: SURVEY.CLOSED},
                    synchronize_session=False)
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
