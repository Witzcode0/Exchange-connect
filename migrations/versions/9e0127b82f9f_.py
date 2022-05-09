"""empty message

Revision ID: 9e0127b82f9f
Revises: 0c3862dbd686
Create Date: 2018-08-18 13:35:29.769931

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9e0127b82f9f'
down_revision = '0c3862dbd686'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint('c_survey_id_email_key', 'survey_response', ['survey_id', 'email'])
    op.create_unique_constraint('c_survey_id_user_id_key', 'survey_response', ['survey_id', 'user_id'])
    op.create_check_constraint('c_check_srvrsp_user_id_email_not_all_null_key', 'survey_response', '((user_id IS NOT NULL) OR (email IS NOT NULL))')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('c_survey_id_user_id_key', 'survey_response', type_='unique')
    op.drop_constraint('c_survey_id_email_key', 'survey_response', type_='unique')
    op.drop_constraint('c_check_srvrsp_user_id_email_not_all_null_key', 'survey_response', type_='check')
    # ### end Alembic commands ###