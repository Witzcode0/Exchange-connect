"""empty message

Revision ID: 90134cc29cae
Revises: e3a0435f7ed1
Create Date: 2020-01-27 14:26:21.663889

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '90134cc29cae'
down_revision = '4d47667ba22d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###

    op.add_column('ref_project_type', sa.Column(
        'is_active', sa.Boolean(), nullable=False, server_default='1'))
    op.execute("update ref_project_type  set is_active = '0' "
               "where project_type_name = 'Build Corporate Website';")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('ref_project_type', 'is_active')

    # ### end Alembic commands ###
