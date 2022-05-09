"""
Helpers for newswire post package
"""

import os
from flask import current_app, Response, jinja2

from app.newswire_resources.newswire_posts.models import NewswirePost


template_dir = os.path.join(os.path.dirname(__file__), 'templates')

jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(
    template_dir), autoescape=True)


def create_newswirepost_template(row_id, previous_version=None):
    """
    used for getting data to create news post xml
    :param row_id:
        row_id of newswire post for which post have to be created
    :param previous_version:
        if newswire post is getting updated then previous version information
    """
    try:
        # status calculate and update in project table
        newswire_post = NewswirePost.query.get(row_id)
        # whether city should also be passed as parameter in newswire model\
        # or not, if not then user city (needs discussion)
        newswire_meta_data = {
            'name': newswire_post.creator.profile.first_name + ' ' +
            newswire_post.creator.profile.last_name,
            'designation': newswire_post.creator.profile.designation,
            'city': ''}

        newswire_item_data = {
            'created_on': newswire_post.created_date,
            'updated_on': newswire_post.modified_date,
            'version': '',
            'headline': newswire_post.headline
        }
        # #TODO: what should be the company_name, either the one provided in
        # model or the account name associated with the newswire post
        # (needs discussion)
        # if 'company_name' in newswire_post:
        #     service_provider = newswire_post.company_name
        # else:
        #     service_provider = newswire_post.account.account_name
        # newswire_item_data.update({'service_provider': service_provider})
        # #TODO: to be added once version is added to model
        # previous version information can also be added to the newswire
        # if previous_version is not None:
        #     newswire_item_data.update({'previous_version': previous_version})
        # #TODO: needs discussion
        # whether editor's note should be added to the data or not
        # if ('editors_note' in newswire_post and
        #         newswire_post.editors_note is not None):
        #     newswire_item_data.update(
        #         {'editors_note': newswire_post.editors_note})
        # #TODO: needs discussion
        # whether availability of creator should be added to the data or not
        # if ('availability' in newswire_post and
        #         newswire_post.availability is not None):
        #     newswire_meta_data.update(
        #         {'availability': newswire_post.availability})
        # #TODO: sub_heading for text and picture part should be different or\
        # same, based on that text and picture information will be added to xml
        # if ('text_sub_heading' in newswire_post and
        #         newswire_post.text_sub_heading is not None):
        #     texts = [{'sub_heading': newswire_post.text_sub_heading,
        #               'body': newswire_post.body_text}]
        #     newswire_item_data.update({'text_data': texts})
        # if ('image_sub_heading' in newswire_post and
        #         newswire_post.image_sub_heading is not None):
        #     images = [{'sub_heading': newswire_post.image_sub_heading,
        #                'url': newswire_post.logo_file.file_url,
        #                'body': newswire_post.image_body}]
        #     newswire_item_data.update({'image_data': images})

        template = jinja_env.get_template('package_template.xml')
        create_template = template.render(
            meta_data=newswire_meta_data, item_data=newswire_item_data)
        print(create_template)
        return Response(create_template, mimetype='text/xml')

    except Exception as e:
        current_app.logger.exception(e)
        raise e
    return
