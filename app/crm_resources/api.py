"""
CRM resources apis
"""

from flask import Blueprint

from app import CustomBaseApi

from app.crm_resources.crm_contacts.api import (
    CRMContactAPI, CRMContactListAPI, CRMCommonContactListAPI, CRMContactBulkDeletAPI)

from app.crm_resources.crm_file_library.api import (
    CRMLibraryFileAPI, CRMLibraryFileListAPI)

from app.crm_resources.crm_contact_notes.api import (
    CRMContactNoteAPI, CRMContactNoteListAPI)

from app.crm_resources.crm_groups.api import (
    CRMGroupAPI, CRMGroupListAPI, BulkGroupContactAPI)

from app.crm_resources.crm_distribution_lists.api import (
    CRMDistributionAPI, CRMDistributionListAPI, UserDistListMonthWiseStatsAPI)

from app.crm_resources.crm_distribution_file_library.api import (
    CRMDistributionLibraryFileAPI, CRMDistributionLibraryFileListAPI)

crm_api_bp = Blueprint('crm_api', __name__, url_prefix='/api/crm/v1.0')
crm_api = CustomBaseApi(crm_api_bp)

# contact apis
crm_api.add_resource(CRMContactListAPI, '/crm-contacts')
crm_api.add_resource(CRMContactAPI, '/crm-contacts', methods=['POST'],
                     endpoint='crmcontactpostapi')
crm_api.add_resource(CRMContactAPI, '/crm-contacts/<int:row_id>', methods=[
    'PUT', 'GET', 'DELETE'])
crm_api.add_resource(CRMContactBulkDeletAPI, '/crm-contacts-bulk-delete', methods=[
    'PUT'])

crm_api.add_resource(BulkGroupContactAPI, '/bulk-group-contacts',
                     methods=['POST'])

crm_api.add_resource(CRMCommonContactListAPI, '/crm-common-contacts')

# CRM file library
crm_api.add_resource(CRMLibraryFileListAPI, '/crm-library-files')
crm_api.add_resource(CRMLibraryFileAPI, '/crm-library-files', methods=['POST'],
                     endpoint='crmlibraryfilepostapi')
crm_api.add_resource(CRMLibraryFileAPI, '/crm-library-files/<int:row_id>',
                     methods=['DELETE', 'GET'])

# CRM Group apis
crm_api.add_resource(CRMGroupListAPI, '/crm-groups')
crm_api.add_resource(CRMGroupAPI, '/crm-groups', methods=['POST'],
                     endpoint='crmgrouppostapi')
crm_api.add_resource(CRMGroupAPI, '/crm-groups/<int:row_id>',
                     methods=['PUT', 'DELETE', 'GET'])

# CRM Contact Note apis
crm_api.add_resource(CRMContactNoteListAPI, '/crm-contact-notes')
crm_api.add_resource(CRMContactNoteAPI, '/crm-contact-notes', methods=['POST'],
                     endpoint='crmcontactnotepostapi')
crm_api.add_resource(CRMContactNoteAPI, '/crm-contact-notes/<int:row_id>',
                     methods=['PUT', 'DELETE', 'GET'])

# CRM Distribution List apis
crm_api.add_resource(CRMDistributionListAPI, '/crm-distribution-lists')
crm_api.add_resource(CRMDistributionAPI, '/crm-distribution-lists',
                     methods=['POST'], endpoint='crmdistributionspostapi')
crm_api.add_resource(CRMDistributionAPI, '/crm-distribution-lists/<int:row_id>',
                     methods=['PUT', 'GET', 'DELETE'])

# CRM file library
crm_api.add_resource(
    CRMDistributionLibraryFileListAPI, '/crm-distribution-library-files')
crm_api.add_resource(CRMDistributionLibraryFileAPI,
                     '/crm-distribution-library-files', methods=['POST'],
                     endpoint='crmdistributionlibraryfilepostapi')
crm_api.add_resource(CRMDistributionLibraryFileAPI,
                     '/crm-distribution-library-files/<int:row_id>',
                     methods=['DELETE', 'GET'])
# CRM distribution lists month wise
crm_api.add_resource(UserDistListMonthWiseStatsAPI,
                     '/user-dist-list-month-wise', methods=['GET'])