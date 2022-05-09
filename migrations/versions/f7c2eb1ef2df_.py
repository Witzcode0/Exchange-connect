"""empty message

Revision ID: f7c2eb1ef2df
Revises: d7771cfb467e
Create Date: 2019-08-09 07:53:13.403968

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f7c2eb1ef2df'
down_revision = 'd7771cfb467e'
branch_labels = None
depends_on = None


def upgrade():
    #op.add_column('menu', sa.Column('code', sa.String(length=64), nullable=True))
    # op.execute('update menu set code = id;')
    # op.create_unique_constraint(None, 'menu', ['code'])
    # op.alter_column(
    #     table_name='menu',
    #     column_name='code',
    #     nullable=False
    # )
    pass
    # ### end Alembic commands ###


def downgrade():
    op.drop_constraint(None, 'menu', type_='unique')
    op.drop_column('menu', 'code')
    # ### end Alembic commands ###
