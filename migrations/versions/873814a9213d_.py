"""empty message

Revision ID: 873814a9213d
Revises: b64ae57275f5
Create Date: 2018-03-15 19:22:51.936016

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '873814a9213d'
down_revision = 'b64ae57275f5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('country',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('created_date', sa.DateTime(), nullable=True),
    sa.Column('modified_date', sa.DateTime(), nullable=True),
    sa.Column('country_name', sa.String(length=128), nullable=False),
    sa.Column('created_by', sa.BigInteger(), nullable=False),
    sa.Column('updated_by', sa.BigInteger(), nullable=False),
    sa.Column('deleted', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], name='country_created_by_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['updated_by'], ['user.id'], name='country_updated_by_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('country_name')
    )
    op.create_table('state',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('created_date', sa.DateTime(), nullable=True),
    sa.Column('modified_date', sa.DateTime(), nullable=True),
    sa.Column('state_name', sa.String(length=128), nullable=False),
    sa.Column('created_by', sa.BigInteger(), nullable=False),
    sa.Column('updated_by', sa.BigInteger(), nullable=False),
    sa.Column('country_id', sa.BigInteger(), nullable=False),
    sa.Column('deleted', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['country_id'], ['country.id'], name='state_country_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], name='state_created_by_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['updated_by'], ['user.id'], name='state_updated_by_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('country_id', 'state_name', name='c_country_id_state_name_key')
    )
    op.create_table('city',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('created_date', sa.DateTime(), nullable=True),
    sa.Column('modified_date', sa.DateTime(), nullable=True),
    sa.Column('city_name', sa.String(length=128), nullable=False),
    sa.Column('created_by', sa.BigInteger(), nullable=False),
    sa.Column('updated_by', sa.BigInteger(), nullable=False),
    sa.Column('country_id', sa.BigInteger(), nullable=False),
    sa.Column('state_id', sa.BigInteger(), nullable=False),
    sa.Column('deleted', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['country_id'], ['country.id'], name='city_country_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], name='city_created_by_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['state_id'], ['state.id'], name='city_state_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['updated_by'], ['user.id'], name='city_updated_by_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('country_id', 'state_id', 'city_name', name='c_country_id_state_id_city_name_key')
    )
    op.add_column('corporate_access_event', sa.Column('city_id', sa.BigInteger(), nullable=True))
    op.add_column('corporate_access_event', sa.Column('country_id', sa.BigInteger(), nullable=True))
    op.add_column('corporate_access_event', sa.Column('state_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key('corporate_access_event_state_id_fkey', 'corporate_access_event', 'state', ['state_id'], ['id'])
    op.create_foreign_key('corporate_access_event_country_id_fkey', 'corporate_access_event', 'country', ['country_id'], ['id'])
    op.create_foreign_key('corporate_access_event_city_id_fkey', 'corporate_access_event', 'city', ['city_id'], ['id'])
    op.drop_column('corporate_access_event', 'country')
    op.drop_column('corporate_access_event', 'city')
    op.drop_column('corporate_access_event', 'state')
    op.add_column('corporate_access_event_slot', sa.Column('slot_name', sa.String(length=256), nullable=True))
    op.add_column('corporate_access_event_slot', sa.Column('text_1', sa.String(length=256), nullable=True))
    op.add_column('corporate_access_event_slot', sa.Column('text_2', sa.String(length=256), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('corporate_access_event_slot', 'text_2')
    op.drop_column('corporate_access_event_slot', 'text_1')
    op.drop_column('corporate_access_event_slot', 'slot_name')
    op.add_column('corporate_access_event', sa.Column('state', sa.VARCHAR(length=64), autoincrement=False, nullable=True))
    op.add_column('corporate_access_event', sa.Column('city', sa.VARCHAR(length=64), autoincrement=False, nullable=True))
    op.add_column('corporate_access_event', sa.Column('country', sa.VARCHAR(length=64), autoincrement=False, nullable=True))
    op.drop_constraint('corporate_access_event_city_id_fkey', 'corporate_access_event', type_='foreignkey')
    op.drop_constraint('corporate_access_event_country_id_fkey', 'corporate_access_event', type_='foreignkey')
    op.drop_constraint('corporate_access_event_state_id_fkey', 'corporate_access_event', type_='foreignkey')
    op.drop_column('corporate_access_event', 'state_id')
    op.drop_column('corporate_access_event', 'country_id')
    op.drop_column('corporate_access_event', 'city_id')
    op.drop_table('city')
    op.drop_table('state')
    op.drop_table('country')
    # ### end Alembic commands ###
