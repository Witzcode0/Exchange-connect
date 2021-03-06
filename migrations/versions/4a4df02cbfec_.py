"""empty message

Revision ID: 4a4df02cbfec
Revises: 504c6e35bd49
Create Date: 2018-06-13 17:21:43.982244

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4a4df02cbfec'
down_revision = '504c6e35bd49'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('account_profile', 'description',
               existing_type=sa.VARCHAR(length=2048),
               type_=sa.String(length=9216),
               existing_nullable=True)
    op.alter_column('company', 'ISIN_number', new_column_name='isin_number')
    op.alter_column('company', 'SEDOL', new_column_name='sedol')
    op.alter_column('corporate_access_event', 'description',
               existing_type=sa.VARCHAR(length=2048),
               type_=sa.String(length=9216),
               existing_nullable=True)
    op.alter_column('event', 'description',
               existing_type=sa.VARCHAR(length=2048),
               type_=sa.String(length=9216),
               existing_nullable=False)
    op.alter_column('management_profile', 'description',
               existing_type=sa.VARCHAR(length=2048),
               type_=sa.String(length=9216),
               existing_nullable=True)
    op.alter_column('post', 'description',
               existing_type=sa.VARCHAR(length=2048),
               type_=sa.String(length=9216),
               existing_nullable=True)
    op.alter_column('survey', 'agenda',
               existing_type=sa.VARCHAR(length=2048),
               type_=sa.String(length=9216),
               existing_nullable=True)
    op.alter_column('user_profile', 'about',
               existing_type=sa.VARCHAR(length=2048),
               type_=sa.String(length=9216),
               existing_nullable=True)
    op.alter_column('webcast', 'description',
               existing_type=sa.VARCHAR(length=2048),
               type_=sa.String(length=9216),
               existing_nullable=True)
    op.alter_column('webinar', 'description',
               existing_type=sa.VARCHAR(length=2048),
               type_=sa.String(length=9216),
               existing_nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('webinar', 'description',
               existing_type=sa.String(length=9216),
               type_=sa.VARCHAR(length=2048),
               existing_nullable=True)
    op.alter_column('webcast', 'description',
               existing_type=sa.String(length=9216),
               type_=sa.VARCHAR(length=2048),
               existing_nullable=True)
    op.alter_column('user_profile', 'about',
               existing_type=sa.String(length=9216),
               type_=sa.VARCHAR(length=2048),
               existing_nullable=True)
    op.alter_column('survey', 'agenda',
               existing_type=sa.String(length=9216),
               type_=sa.VARCHAR(length=2048),
               existing_nullable=True)
    op.alter_column('post', 'description',
               existing_type=sa.String(length=9216),
               type_=sa.VARCHAR(length=2048),
               existing_nullable=True)
    op.alter_column('management_profile', 'description',
               existing_type=sa.String(length=9216),
               type_=sa.VARCHAR(length=2048),
               existing_nullable=True)
    op.alter_column('event', 'description',
               existing_type=sa.String(length=9216),
               type_=sa.VARCHAR(length=2048),
               existing_nullable=False)
    op.alter_column('corporate_access_event', 'description',
               existing_type=sa.String(length=9216),
               type_=sa.VARCHAR(length=2048),
               existing_nullable=True)
    op.alter_column('company', 'isin_number', new_column_name='ISIN_number')
    op.alter_column('company', 'sedol', new_column_name='SEDOL')
    op.alter_column('account_profile', 'description',
               existing_type=sa.String(length=9216),
               type_=sa.VARCHAR(length=2048),
               existing_nullable=True)
    # ### end Alembic commands ###
