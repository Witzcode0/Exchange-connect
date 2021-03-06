"""empty message

Revision ID: 57f3b3e6dc37
Revises: 4937486efe48
Create Date: 2021-01-20 12:08:10.540888

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '57f3b3e6dc37'
down_revision = '080193de7517'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    """op.create_table('fundmanagement',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('created_date', sa.DateTime(), nullable=True),
    sa.Column('modified_date', sa.DateTime(), nullable=True),
    sa.Column('crm_contact_id', sa.BigInteger(), nullable=False),
    sa.Column('entity_proper_name', sa.String(), nullable=False),
    sa.Column('factset_fund_id', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['crm_contact_id'], ['crm_contact.id'], name='fundmanagement_crm_contact_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('crm_contact', sa.Column('factset_person_id', sa.String(length=128), nullable=True))
    op.add_column('crm_contact', sa.Column('about', sa.String(), nullable=True))
    op.add_column('crm_contact', sa.Column('is_company_profile', sa.Boolean(), nullable=True))
    op.drop_column('crm_contact', 'fund_managed')
    """    # ### end Alembic commands ###
    pass

def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('crm_contact', sa.Column('fund_managed', postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True))
    op.drop_column('crm_contact', 'is_company_profile')
    op.drop_column('crm_contact', 'about')
    op.drop_column('crm_contact', 'factset_person_id')
    op.drop_table('fundmanagement')
    # ### end Alembic commands ###
