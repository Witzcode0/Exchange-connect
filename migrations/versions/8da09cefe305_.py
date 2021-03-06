"""empty message

Revision ID: 8da09cefe305
Revises: 0fa096bc5de8
Create Date: 2020-02-20 15:10:37.551941

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '8da09cefe305'
down_revision = 'e3a0435f7ed1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('project', sa.Column('annual_report_type', sa.String(length=256), nullable=True))
    op.add_column('project', sa.Column('report_height', sa.String(length=32), nullable=True))
    op.add_column('project', sa.Column('report_theme', sa.String(), nullable=True))
    op.add_column('project', sa.Column('report_width', sa.String(length=32), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('project', 'report_width')
    op.drop_column('project', 'report_theme')
    op.drop_column('project', 'report_height')
    op.drop_column('project', 'annual_report_type')
    # ### end Alembic commands ###
