"""empty message

Revision ID: 6770adb786ae
Revises: 70a96bc7c85d
Create Date: 2018-03-21 15:12:17.004279

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6770adb786ae'
down_revision = '70a96bc7c85d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ci_account_unique_account_name', 'account', [sa.text('lower(account_name)')], unique=True)


def downgrade():
    op.drop_index('ci_account_unique_account_name', 'account')
