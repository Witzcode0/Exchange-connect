# announcement category upload
import datetime

from app import db

from flask_script import Command, Option
from app.resources.corporate_announcements_category.models import (
    CorporateAnnouncementCategory)
from app.resources.corporate_announcements_category.schemas import (
    AdminCorporateAnnouncementCategorySchema)
import pandas as pd
from sqlalchemy.exc import IntegrityError


class AddCorporateAnnouncementCategory(Command):
    """
    Command to import category data from xlsx file

    :arg verbose:
        print progress
    :arg dry:
        dry run
    """

    option_list = [
        Option('--verbose', '-v', dest='verbose', action='store_true',
               default=False),
        Option('--dry', '-dry', dest='dry', action='store_true',
               default=False),
        Option('--user_id', '-user', dest='user_id', required=True),
        Option('--csv_file', '-csv', dest='csv_file', required=True),
    ]

    def run(self, verbose, dry, csv_file, user_id):
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('Adding Corporate announcements category ...')
        try:
            if csv_file:
                # check file is csv
                colnames=[ 'keywords', 'category']
                cat_df = pd.read_csv(csv_file, names=colnames, header=0)
                print(cat_df)

                #groupby category and keywords
                new_df = cat_df.groupby('category')['keywords'].apply(lambda group_series: group_series.tolist()).reset_index()
                
                new_list = new_df.values.tolist()
                for sub_list in new_list:
                    cat = CorporateAnnouncementCategory.query.filter(
                            CorporateAnnouncementCategory.name == sub_list[0].lower()).one()
                    
                    if cat:
                        cat.updated_by = user_id
                        subject_keywords_list = cat.subject_keywords
                        if subject_keywords_list:
                            cat.subject_keywords = sub_list[1] + subject_keywords_list
                        else:
                            cat.subject_keywords = sub_list[1]
                        
                    try:
                        db.session.add(cat)
                        db.session.commit()

                    except IntegrityError as e:
                        db.session.rollback()
                
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)