"""empty message

Revision ID: e3fb7fbc3339
Revises: a86ef8e7c97e
Create Date: 2018-08-09 16:24:04.500729

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import app

# revision identifiers, used by Alembic.
revision = 'e3fb7fbc3339'
down_revision = 'a86ef8e7c97e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.rename_table('contact_us', 'inquiry')
    op.execute('ALTER SEQUENCE contact_us_id_seq RENAME TO inquiry_id_seq')
    op.execute('ALTER INDEX contact_us_pkey RENAME TO inquiry_pkey')
    op.drop_constraint('contact_us_updated_by_fkey', 'inquiry', type_='foreignkey')
    op.add_column('inquiry', sa.Column('inquiry_type', app.base.model_fields.ChoiceString(app.resources.inquiries.constants.INQ_TYPE_TYPE_CHOICES)))
    op.execute(
        "UPDATE inquiry SET inquiry_type='" + app.resources.inquiries.constants.INQT_CONTACT + "'")
    op.alter_column('inquiry', 'inquiry_type', nullable=False)
    op.add_column('inquiry', sa.Column('major_sub_type', app.base.model_fields.ChoiceString(app.resources.inquiries.constants.INQT_ALL_TYPE_CHOICES), nullable=True))
    op.add_column('inquiry', sa.Column('account_id', sa.BigInteger(), nullable=True))
    op.add_column('inquiry', sa.Column('created_by', sa.BigInteger(), nullable=True))
    op.create_foreign_key('inquiry_account_id_fkey', 'inquiry', 'account', ['account_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('inquiry_created_by_fkey', 'inquiry', 'user', ['created_by'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('inquiry_updated_by_fkey', 'inquiry', 'user', ['updated_by'], ['id'], ondelete='SET NULL')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('inquiry_account_id_fkey', 'inquiry', type_='foreignkey')
    op.drop_column('inquiry', 'account_id')
    op.drop_constraint('inquiry_created_by_fkey', 'inquiry', type_='foreignkey')
    op.drop_column('inquiry', 'created_by')
    op.drop_constraint('inquiry_updated_by_fkey', 'inquiry', type_='foreignkey')
    op.drop_column('inquiry', 'inquiry_type')
    op.drop_column('inquiry', 'major_sub_type')

    op.rename_table('inquiry', 'contact_us')
    op.execute('ALTER SEQUENCE inquiry_id_seq RENAME TO contact_us_id_seq')
    op.execute('ALTER INDEX inquiry_pkey RENAME TO contact_us_pkey')
    op.create_foreign_key('contact_us_updated_by_fkey', 'contact_us', 'user', ['updated_by'], ['id'], ondelete='SET NULL')

    # ### end Alembic commands ###