"""empty message

Revision ID: e39a711d4bec
Revises: 35d81f89a521
Create Date: 2021-10-01 12:44:07.903266

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e39a711d4bec'
down_revision = '35d81f89a521'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('corporate_announcement', 'category',
               existing_type=sa.VARCHAR(),
               nullable=True)
    #op.drop_column('crm_contact', 'industry')
    #op.alter_column('personalised_video_invitee', 'account_id',
    #           existing_type=sa.INTEGER(),
    #           nullable=False)
    #op.create_foreign_key(None, 'personalised_video_invitee', 'account', ['account_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    #op.drop_constraint(None, 'personalised_video_invitee', type_='foreignkey')
    #op.alter_column('personalised_video_invitee', 'account_id',
    #           existing_type=sa.INTEGER(),
    #           nullable=True)
    #op.add_column('crm_contact', sa.Column('industry', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.alter_column('corporate_announcement', 'category',
               existing_type=sa.VARCHAR(),
               nullable=False)
    # ### end Alembic commands ###
