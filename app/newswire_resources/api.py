"""
Newswire resources apis
"""

from flask import Blueprint

from app.newswire_resources.newswire_posts.api import (
    NewswirePostAPI, NewswirePostListAPI)

from app import CustomBaseApi

from app.newswire_resources.newswire_post_file_library.api import (
    NewswirePostLibraryFileAPI, NewswirePostLibraryFileListAPI)


newswire_api_bp = Blueprint('newswire_api', __name__,
                            url_prefix='/api/newswire/v1.0')
newswire_api = CustomBaseApi(newswire_api_bp)


# News wire post
newswire_api.add_resource(
    NewswirePostAPI, '/news-wire-posts', methods=['POST'],
    endpoint='newswirepostpostapi')
newswire_api.add_resource(NewswirePostAPI, '/news-wire-posts/<int:row_id>',
                          methods=['DELETE', 'GET', 'PUT'])
newswire_api.add_resource(NewswirePostListAPI, '/news-wire-posts')

# newswire_post_file_library
newswire_api.add_resource(NewswirePostLibraryFileListAPI,
                          '/newswire-post-file-library')
newswire_api.add_resource(NewswirePostLibraryFileAPI,
                          '/newswire-post-file-library/<int:row_id>',
                          methods=['GET', 'PUT', 'DELETE'])
newswire_api.add_resource(NewswirePostLibraryFileAPI,
                          '/newswire-post-file-library', methods=['POST'],
                          endpoint='newswirepostfilelibraryapi')
