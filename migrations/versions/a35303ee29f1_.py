"""empty message

Revision ID: a35303ee29f1
Revises: ad732cfdad89
Create Date: 2018-11-14 14:56:47.084776

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import app


# revision identifiers, used by Alembic.
revision = 'a35303ee29f1'
down_revision = 'ad732cfdad89'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user_settings', sa.Column('crm_customize_view', app.base.model_fields.CastingArray(postgresql.JSONB(astext_type=sa.Text())), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user_settings', 'crm_customize_view')
    # ### end Alembic commands ###
