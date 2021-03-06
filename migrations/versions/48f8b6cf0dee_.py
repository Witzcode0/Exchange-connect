"""empty message

Revision ID: 48f8b6cf0dee
Revises: 7603041c70f0
Create Date: 2020-04-17 22:14:22.499844

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import datetime

# revision identifiers, used by Alembic.
revision = '48f8b6cf0dee'
down_revision = '7603041c70f0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('news_announcements',
                  sa.Column('market_comment_id', sa.BigInteger(),
                            nullable=True))
    op.add_column('news_announcements',
                  sa.Column('market_permission_choice', sa.Boolean(),
                            nullable=True))
    op.add_column('news_announcements',
                  sa.Column('market_permission_id', sa.BigInteger(),
                            nullable=True))
    op.alter_column('news_announcements', 'account_id',
                    existing_type=sa.BIGINT(),
                    nullable=True)
    op.create_foreign_key('market_comment_id_fkey', 'news_announcements',
                          'market_analyst_comment', ['market_comment_id'],
                          ['id'], ondelete='CASCADE')
    op.create_foreign_key('market_performance_id_fkey', 'news_announcements',
                          'market_performance', ['market_permission_id'],
                          ['id'], ondelete='CASCADE')
    # #todo: remove above commands
    # #todo: uncomment
    # op.execute('''CREATE OR REPLACE FUNCTION news_insert() RETURNS trigger AS
    #               $$ BEGIN INSERT INTO news_announcements(news_id, account_id,created_date) VALUES(NEW.news_id,NEW.account_id,now()); RETURN NEW;
    #               END; $$ LANGUAGE 'plpgsql';''')
    # op.execute('''CREATE TRIGGER news_rec
    #               AFTER INSERT
    #               ON newsaccounts
    #               FOR EACH ROW
    #               EXECUTE PROCEDURE news_insert();''')
    # op.execute('''CREATE OR REPLACE FUNCTION rec_insert() RETURNS trigger AS
    #               $$ BEGIN INSERT INTO news_announcements(announcements_id, account_id,created_date) VALUES(NEW.id,NEW.account_id,now()); RETURN NEW;
    #               END; $$ LANGUAGE 'plpgsql';''')
    # op.execute('''CREATE TRIGGER ins_same_rec
    #               AFTER INSERT
    #               ON corporate_announcement
    #               FOR EACH ROW
    #               EXECUTE PROCEDURE rec_insert();''')
    op.execute('''CREATE OR REPLACE FUNCTION per_insert() RETURNS trigger AS 
                  $$ BEGIN INSERT INTO news_announcements(
                  market_permission_id,account_id,market_permission_choice,
                  created_date) VALUES(NEW.id,NEW.account_id,
                  NEW.account_id_null_boolean,now()); RETURN NEW;
                  END; $$ LANGUAGE 'plpgsql';''')
    op.execute('''CREATE TRIGGER per_rec
                  AFTER INSERT
                  ON market_performance
                  FOR EACH ROW
                  EXECUTE PROCEDURE per_insert();''')
    op.execute('''CREATE OR REPLACE FUNCTION comment_insert() RETURNS trigger
                  AS $$ BEGIN INSERT INTO news_announcements(
                  market_comment_id,created_date) 
                  VALUES(NEW.id,now());
                  RETURN NEW;
                  END; $$ LANGUAGE 'plpgsql';''')
    op.execute('''CREATE TRIGGER comment_rec
                  AFTER INSERT
                  ON market_analyst_comment
                  FOR EACH ROW
                  EXECUTE PROCEDURE comment_insert();''')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute('drop trigger news_rec on newsaccounts;')
    op.execute('drop trigger ins_same_rec on corporate_announcement;')
    op.execute('drop trigger per_rec on market_performance;')
    op.execute('drop trigger comment_rec on market_analyst_comment;')
    # ### end Alembic commands ###
