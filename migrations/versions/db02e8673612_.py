"""empty message

Revision ID: db02e8673612
Revises: ab13c1b3ee5b
Create Date: 2018-07-09 19:49:51.916942

"""
from alembic import op
import sqlalchemy as sa
import app
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'db02e8673612'
down_revision = 'ab13c1b3ee5b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('corporate_access_event', sa.Column('cc_emails', postgresql.ARRAY(app.base.model_fields.LCString(length=128)), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('corporate_access_event', 'cc_emails')
    # ### end Alembic commands ###
