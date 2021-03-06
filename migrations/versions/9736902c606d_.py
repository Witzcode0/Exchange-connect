"""empty message

Revision ID: 9736902c606d
Revises: 308b125d7992
Create Date: 2019-05-01 16:24:01.481583

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import app
from app.base import constants as APP

# revision identifiers, used by Alembic.
revision = '9736902c606d'
down_revision = '308b125d7992'
branch_labels = None
depends_on = None
choices = app.base.model_fields.ChoiceString(APP.EMAIL_STATUS_CHOICES)

altered_tables = [
                  "webinar_host",
                  "webinar_invitee",
                  "webinar_participant",
                  "webinar_rsvp",
                  "webcast_host",
                  "webcast_invitee",
                  "webcast_participant",
                  "webcast_rsvp",
                  "survey_response",
                  "crm_distribution_invitee_list",
                  ]


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    for table in altered_tables:
        op.add_column(table,
                      sa.Column('email_status', choices, nullable=False,
                                server_default=APP.EMAIL_SENT))
        update_query = "update {} set email_status=case when is_mail_sent='t' then '{}' when is_mail_sent= 'f' then '{}' end;"
        op.execute(
            update_query.format(table, APP.EMAIL_SENT, APP.EMAIL_NOT_SENT))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    for table in altered_tables:
        op.drop_column(table, 'email_status')

    # ### end Alembic commands ###
