"""empty message

Revision ID: 28926377d629
Revises: 87f59537eb11
Create Date: 2020-08-27 15:48:45.393597

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import app

# revision identifiers, used by Alembic.
revision = '28926377d629'
down_revision = '87f59537eb11'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # op.add_column('email_static', sa.Column('email_category', app.base.model_fields.ChoiceString(app.base.constants.EMAIL_TYEPS), nullable=True))
    pass
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('email_static', 'email_category')
    # ### end Alembic commands ###