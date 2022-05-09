"""
Store some constants related to the projects module
"""

# maximum length constraints
NAME_MAX_LENGTH = 256
INST_MAX_LENGTH = 1024

DESIGN = 'design'
CONTENT = 'content'
DESIGN_CONTENT = 'design_content'
WORK_ARIAS = [DESIGN, CONTENT, DESIGN_CONTENT]
WORK_ARIA_CHOICES = [(x, x) for x in WORK_ARIAS]

WORK_ARIA_VERBOSE = {
    DESIGN: "Design & Presentation",
    CONTENT: "Content Development",
    DESIGN_CONTENT: "Complete Project"
}

WIDE = 'wide'
STANDARD = 'standard'
SPECIFIC = 'specific'
DIMENTION_TYPES = [WIDE, STANDARD, SPECIFIC]
DIMENTION_TYPES_CHOICES = [(x, x) for x in DIMENTION_TYPES]


CURRENT_PRESENTATION = 'current_presentation_file'
COMP_LOGO = 'company_logo_file'
BRAND_IDENTITY = 'brand_identity_file'
OTHER_FILE = 'other_file'
TEMPLATE = 'template_file'
PRESENTATION = 'presentation_file'
FINAL_FILE = 'final_file'
COMPANY_MATERIAL = 'company_material_file'
PROJECT_FILE_CATEGORY = [CURRENT_PRESENTATION, COMP_LOGO, BRAND_IDENTITY,
    OTHER_FILE, TEMPLATE, PRESENTATION, FINAL_FILE, COMPANY_MATERIAL]
PROJECT_FILE_CATEGORY_CHOICES = [(x, x) for x in PROJECT_FILE_CATEGORY]

# file category and status name mapping
CATEGORY_STATUS_CODE = {
    TEMPLATE: "template_received",
    PRESENTATION: "presentation_received",
    FINAL_FILE: "completed"
}

# project codes constants
ASSIGNED = "proj_assigned"
INTRO_CALL = "intro_call"
TEMPLATE_DESIGNING = "template_designing"
TEMPLATE_RECV = "template_received"
TEMPLATE_APPROVED = "template_approved"
MAIN_PRESENTATION = "main_presentation"
PRESENTATION_RECV = "presentation_received"
COMPLETED = "completed"

NOTIFY_CLIENT_STATUSES = [ASSIGNED, TEMPLATE_DESIGNING, TEMPLATE_RECV,
    MAIN_PRESENTATION, PRESENTATION_RECV, COMPLETED]
NOTIFY_PRIME_COMMUNICATOR_STATUSES = [TEMPLATE_APPROVED, COMPLETED]
NOTIFY_NON_PRIME_COMMUNICATOR_STATUSES = [INTRO_CALL, TEMPLATE_DESIGNING,
    TEMPLATE_RECV, TEMPLATE_APPROVED, MAIN_PRESENTATION, PRESENTATION_RECV,
    COMPLETED]

APX_PROJECT_TYPES = ["Annual Report", "Corporate Presentation",
    "Earning Presentation", "Investor Presentation", "Factsheet", "Press Release",
    "Newsletter", "Press Release Earning", "ESG or Sustainability Report"]

APX_PROJECT_TYPE_CHOICES = [(x, x) for x in APX_PROJECT_TYPES]