"""empty message

Revision ID: 3a7286aedb7b
Revises: 0c1ae7a9cd70
Create Date: 2018-06-05 17:59:37.600577

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3a7286aedb7b'
down_revision = '0c1ae7a9cd70'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('corporate_access_event', sa.Column('cancelled', sa.Boolean(), nullable=True))
    op.execute("UPDATE corporate_access_event SET cancelled=false")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('corporate_access_event', 'cancelled')
    # ### end Alembic commands ###