"""empty message

Revision ID: 72f2cad79a50
Revises: 2ce3865f8250
Create Date: 2019-01-21 16:31:16.209439

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '72f2cad79a50'
down_revision = '2ce3865f8250'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user_settings', sa.Column('android_request_device_ids', sa.ARRAY(sa.String()), nullable=True))
    op.add_column('user_settings', sa.Column('ios_request_device_ids', sa.ARRAY(sa.String()), nullable=True))
    op.drop_column('user_settings', 'request_device_ids')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user_settings', sa.Column('request_device_ids', postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True))
    op.drop_column('user_settings', 'ios_request_device_ids')
    op.drop_column('user_settings', 'android_request_device_ids')
    # ### end Alembic commands ###