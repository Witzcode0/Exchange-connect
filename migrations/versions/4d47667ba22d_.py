"""empty message

Revision ID: 4d47667ba22d
Revises: 138f2f0a421d
Create Date: 2020-01-09 16:14:37.127298

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4d47667ba22d'
down_revision = '138f2f0a421d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('notification', sa.Column('project_status_code', sa.String(length=32), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('notification', 'project_status_code')
    # ### end Alembic commands ###
