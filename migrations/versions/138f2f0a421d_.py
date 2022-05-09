"""empty message

Revision ID: 138f2f0a421d
Revises: 9b8c5cda3a74
Create Date: 2020-01-06 16:32:55.244787

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '138f2f0a421d'
down_revision = '9b8c5cda3a74'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('notification', sa.Column('project_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key('notification_project_id_fkey', 'notification', 'project', ['project_id'], ['id'], ondelete='CASCADE')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('notification_project_id_fkey', 'notification', type_='foreignkey')
    op.drop_column('notification', 'project_id')
    # ### end Alembic commands ###
