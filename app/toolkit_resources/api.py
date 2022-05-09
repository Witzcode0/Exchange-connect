"""
Toolkit resources apis
"""

from flask import Blueprint

from app.toolkit_resources.ref_project_types.api import (
    RefProjectTypeAPI, RefProjectTypeListAPI)

from app.toolkit_resources.ref_project_sub_type.api import (
RefProjectSubTypeListAPI,RefProjectSubTypeAPI)

from app.toolkit_resources.ref_project_sub_child_type.api import (
RefProjectSubChildTypeListAPI,RefProjectSubChildTypeAPI)

from app.toolkit_resources.project_file_archive.api import (
    ProjectArchiveFileAPI, ProjectArchiveFileListAPI)

from app.toolkit_resources.ref_project_parameters.api import (
    RefProjectParameterAPI, RefProjectParameterListAPI)

from app.toolkit_resources.project_screen_sharings.api import (
    ProjectScreenSharingAPI, ProjectScreenSharingListAPI)

from app.toolkit_resources.project_analysts.api import (
    ProjectAnalystAPI, ProjectAnalystListAPI)

from app.toolkit_resources.project_designers.admin_api import (
    ProjectDesignerAPI, ProjectDesignerListAPI)

from app.toolkit_resources.project_chats.api import (
    ProjectChatMessageAPI, ProjectChatMessageListAPI)

from app.toolkit_resources.projects.api import ProjectAPI, ProjectListAPI
from app.toolkit_resources.projects.apx_api import (
    ProjectApxAPI, ProjectApxListAPI)

from app.toolkit_resources.projects.admin_analyst_api import \
    ProjectAdminAnalystAPI, ProjectAdminAnalystListAPI

from app.toolkit_resources.project_parameters.api import (
    ProjectParameterAPI, ProjectParameterListAPI)
from app.toolkit_resources.project_status.api import ProjectStatusListAPI
from app.toolkit_resources.projects.api import ProjectCancelledAPI

from app.toolkit_resources.project_file_comments.api import (
    ProjectFileCommentAPI, ProjectFileCommentListAPI)

from app import CustomBaseApi

from app.toolkit_resources.project_e_meeting.api import (EmeetingAPI
    ,EmeetingCancelAPI,EmeetingListAPI)

from app.toolkit_resources.project_e_meeting_comment.api import (EmeetingCommentAPI
    ,EmeetingCommentListAPI)

toolkit_api_bp = Blueprint('toolkit_api', __name__,
                           url_prefix='/api/toolkit/v1.0')
toolkit_api = CustomBaseApi(toolkit_api_bp)

# reference project types
toolkit_api.add_resource(RefProjectTypeListAPI, '/ref-project-types')
toolkit_api.add_resource(RefProjectTypeAPI, '/ref-project-types',
                         methods=['POST'], endpoint='refprojecttypepostapi')
toolkit_api.add_resource(RefProjectTypeAPI, '/ref-project-types/<int:row_id>',
                         methods=['GET', 'PUT', 'DELETE'])

# reference project types
toolkit_api.add_resource(RefProjectSubTypeListAPI, '/ref-project-sub-types')
toolkit_api.add_resource(RefProjectSubTypeAPI, '/ref-project-sub-types',
                         methods=['POST'], endpoint='refprojectsubtypepostapi')
# toolkit_api.add_resource(RefProjectTypeAPI, '/ref-project-types/<int:row_id>',
#                          methods=['GET', 'PUT', 'DELETE'])

# reference project child types
toolkit_api.add_resource(RefProjectSubChildTypeListAPI, '/ref-project-sub-child-types')
toolkit_api.add_resource(RefProjectSubChildTypeAPI, '/ref-project-sub-child-types',
                         methods=['POST'], endpoint='refprojectsubchildtypepostapi')

# Project archive file
toolkit_api.add_resource(ProjectArchiveFileListAPI, '/project-archive-files')
toolkit_api.add_resource(ProjectArchiveFileAPI, '/project-archive-files',
                         methods=['POST'],
                         endpoint='projectarchivefilepostapi')
toolkit_api.add_resource(
    ProjectArchiveFileAPI, '/project-archive-files/<int:row_id>',
    methods=['PUT', 'DELETE', 'GET'])

# reference project screen sharing
toolkit_api.add_resource(
    ProjectScreenSharingAPI, '/projects-screen-sharing',
    methods=['POST'], endpoint='projectscreensharingpostapi')
toolkit_api.add_resource(
    ProjectScreenSharingAPI, '/projects-screen-sharing/<int:row_id>',
    methods=['PUT', 'GET', 'DELETE'])
toolkit_api.add_resource(
    ProjectScreenSharingListAPI, '/projects-screen-sharing')

# Projects related api
toolkit_api.add_resource(ProjectAPI, '/projects', methods=['POST'],
                         endpoint='projectpostapi')
toolkit_api.add_resource(ProjectAPI, '/projects/<int:row_id>',
                         methods=['GET', 'PUT', 'DELETE'])
toolkit_api.add_resource(ProjectListAPI, '/projects')
toolkit_api.add_resource(ProjectCancelledAPI, '/project-cancel/<int:row_id>')
toolkit_api.add_resource(
    ProjectAdminAnalystAPI, '/project-admin-analysts/<int:row_id>',
    methods=['PUT', 'GET', 'DELETE'])
toolkit_api.add_resource(ProjectAdminAnalystListAPI, '/project-admin-analysts')
toolkit_api.add_resource(ProjectAdminAnalystAPI, '/project-admin-analysts',
                         endpoint='projectadminanalystpostapi')

# Project parameters related api
toolkit_api.add_resource(ProjectParameterAPI,
                         '/project-parameters', methods=['POST'],
                         endpoint='projectparameterpostapi')
toolkit_api.add_resource(ProjectParameterAPI,
                         '/project-parameters/<int:row_id>',
                         methods=['GET', 'PUT', 'DELETE'])
toolkit_api.add_resource(ProjectParameterListAPI, '/project-parameters')

# reference project parameters
toolkit_api.add_resource(RefProjectParameterListAPI, '/ref-project-parameters')
toolkit_api.add_resource(
    RefProjectParameterAPI, '/ref-project-parameters',
    methods=['POST'], endpoint='refprojectparameterpostapi')
toolkit_api.add_resource(
    RefProjectParameterAPI, '/ref-project-parameters/<int:row_id>',
    methods=['GET', 'PUT', 'DELETE'])

# project_analysts
toolkit_api.add_resource(ProjectAnalystAPI, '/project-analysts',
                         methods=['POST'], endpoint='projectanalystpostapi')
toolkit_api.add_resource(ProjectAnalystAPI, '/project-analysts/<int:row_id>',
                         methods=['GET', 'PUT', 'DELETE'])
toolkit_api.add_resource(ProjectAnalystListAPI, '/project-analysts')

# project_designers
toolkit_api.add_resource(ProjectDesignerAPI, '/project-designers',
                         methods=['POST'], endpoint='projectdesignerpostapi')
toolkit_api.add_resource(ProjectDesignerAPI, '/project-designers/<int:row_id>',
                         methods=['GET', 'PUT', 'DELETE'])
toolkit_api.add_resource(ProjectDesignerListAPI, '/project-designers')

# project_chats
toolkit_api.add_resource(ProjectChatMessageAPI, '/project-chat-messages',
                         methods=['POST'],
                         endpoint='projectchatmessagepostapi')
toolkit_api.add_resource(ProjectChatMessageAPI,
                         '/project-chat-messages/<int:row_id>',
                         methods=['GET', 'PUT', 'DELETE'])
toolkit_api.add_resource(ProjectChatMessageListAPI, '/project-chat-messages')

# project_status
toolkit_api.add_resource(ProjectStatusListAPI, '/project-statuses')

toolkit_api.add_resource(ProjectApxAPI, '/design-lab-projects/<int:row_id>',
                 methods=['GET', 'PUT'])
toolkit_api.add_resource(ProjectApxListAPI, '/design-lab-projects',
                 methods=['GET'])
toolkit_api.add_resource(ProjectApxAPI, '/design-lab-projects',
                 methods=['POST'], endpoint='projectapxpostapi')

# project file comments
toolkit_api.add_resource(
    ProjectFileCommentAPI, '/project-file-comments/<int:row_id>',
    methods=['GET', 'PUT', 'DELETE'])
toolkit_api.add_resource(
    ProjectFileCommentListAPI, '/project-file-comments',
    methods=['GET'])
toolkit_api.add_resource(
    ProjectFileCommentAPI, '/project-file-comments',
    methods=['POST'], endpoint='projectfilecommentpostapi')

# E_meeting apis
toolkit_api.add_resource(EmeetingAPI,'/e_meeting/<int:row_id>',
                 methods=['GET','PUT','DELETE'])
toolkit_api.add_resource(EmeetingCancelAPI,'/e_meeting_cancel/<int:row_id>',
                 methods=['PUT'])
toolkit_api.add_resource(EmeetingAPI,'/e_meeting',
                 methods=['POST'],endpoint='emeetingpostapi')
toolkit_api.add_resource(EmeetingListAPI,'/e_meeting',
                 methods=['GET'])

#e_meeting comment apis
toolkit_api.add_resource(EmeetingCommentAPI,'/e_meeting_comment',
                 methods=['POST'],endpoint='emeetingcommentpostapi')
toolkit_api.add_resource(EmeetingCommentAPI,'/e_meeting_comment/<int:row_id>',
                 methods=['GET','DELETE'])
toolkit_api.add_resource(EmeetingCommentListAPI,'/e_meeting_comment',
                 methods=['GET'])