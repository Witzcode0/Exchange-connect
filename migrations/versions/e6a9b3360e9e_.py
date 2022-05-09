"""empty message

Revision ID: e6a9b3360e9e
Revises: 9bfc1fee7970
Create Date: 2018-01-03 10:03:35.020435

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e6a9b3360e9e'
down_revision = '9bfc1fee7970'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('project', sa.Column('glossary', sa.String(length=256), nullable=True))
    op.add_column('project', sa.Column('link', sa.String(length=256), nullable=True))
    op.add_column('project', sa.Column('special_instructions', sa.String(length=1024), nullable=True))
    op.add_column('project_parameter', sa.Column('parameter_value', sa.String(length=256), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('project_parameter', 'parameter_value')
    op.drop_column('project', 'special_instructions')
    op.drop_column('project', 'link')
    op.drop_column('project', 'glossary')
    # ### end Alembic commands ###