"""empty message

Revision ID: e3a0435f7ed1
Revises: 4d47667ba22d
Create Date: 2020-01-16 12:06:01.119764

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e3a0435f7ed1'
down_revision = '90134cc29cae'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('registration_request', sa.Column(
        'welcome_mail_sent', sa.Boolean(), server_default='1', nullable=True))
    op.add_column('user', sa.Column(
        'verify_mail_sent', sa.Boolean(), server_default='1', nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'verify_mail_sent')
    op.drop_column('registration_request', 'welcome_mail_sent')
    # ### end Alembic commands ###
