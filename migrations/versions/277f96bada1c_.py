"""empty message

Revision ID: 277f96bada1c
Revises: b3c35fd22d8d
Create Date: 2018-12-28 12:28:26.759111

"""
from alembic import op
import sqlalchemy as sa
import app

# revision identifiers, used by Alembic.
revision = '277f96bada1c'
down_revision = 'b3c35fd22d8d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('corporate_access_event', sa.Column('account_type_preference', sa.ARRAY(app.base.model_fields.ChoiceString(app.resources.accounts.constants.ACCT_TYPES_CHOICES)), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('corporate_access_event', 'account_type_preference')
    # ### end Alembic commands ###
