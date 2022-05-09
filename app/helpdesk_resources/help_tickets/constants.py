"""
Store some constants related to "helptickets"
"""

# section values
SEC_AC = 'activity'
SEC_CA = 'corporate access'
SEC_PB = 'peer benchmarking'
SEC_WC = 'webcasting'
SEC_WB = 'webinar'
SEC_PS = 'perception survey'
SEC_ND = 'newswire distribution'
SEC_IRM = 'investor relations modules'
SEC_OTHER = 'other'
SEC_NETWORK = 'my network'
SEC_OA = 'ownership analysis'
SEC_IT = 'investor targeting'
SEC_PSTD = 'perception study'
SEC_DE = 'disclosures enhancement'
SEC_OYD = 'order your documents'
SEC_MP = 'my projects'
SEC_CRM = 'crm'
SEC_SC = 'search company'
SEC_MC = 'my company'
SEC_EVT = 'events'
SEC_CC = 'conference calls'
SEC_SR = 'schedule report'
SEC_DESLAB = 'design lab'

SECTION_TYPES = [SEC_AC, SEC_CA, SEC_PB, SEC_WC, SEC_WB, SEC_PS, SEC_ND,
                 SEC_IRM, SEC_OTHER, SEC_NETWORK, SEC_OA, SEC_IT, SEC_PSTD,
                 SEC_DE, SEC_OYD, SEC_MP, SEC_CRM, SEC_SC, SEC_MC, SEC_EVT,
                 SEC_CC, SEC_SR, SEC_DESLAB]
# for direct use in model definition
SECTION_TYPES_CHOICES = [(v, v) for v in SECTION_TYPES]


# function values
FXN_HM = 'home'
FXN_FO = 'following'
FXN_CS = 'company showcase'
FXN_FC = 'find connection'
FXN_NWS = 'news'
FXN_OV = 'overview'
FXN_EVT = 'events'
FXN_ST = 'statistics'
FXN_DR = 'draft'
FXN_OV2 = 'overview'
FXN_WC = 'webcast'
FXN_DR2 = 'draft'
FXN_UC = 'upcoming'
FXN_ST2 = 'statistics'
FXN_OV3 = 'overview'
FXN_WN = 'webinar'
FXN_SVY = 'survey'
FXN_DR3 = 'draft'
FXN_NW = 'newswire'
FXN_IRM = 'investor relations modules'
FXN_CIR = 'concept of investor relations'
FXN_OCID = 'organizing and conducting investor day'
FXN_OTHER = 'other'
FXN_AC = 'activity'
FXN_FL = 'followers'
FXN_CWEB = 'company webpage'
FXN_MN = 'my network'
FXN_MC = 'my connections'
FXN_SC = 'search company'
FXN_SP = 'search people'
FXN_SRQ = 'sent requests'
FXN_CRQ = 'contact requests'
FXN_CA = 'corporate access'
FXN_OFE = 'open for event'
FXN_AVL = 'availability'
FXN_CE = 'create event'
FXN_OA = 'ownership analysis'
FXN_S = 'snapshot'
FXN_BS = 'buyer/seller'
FXN_CO = 'comprehensive ownership'
FXN_H = 'historical'
FXN_GD = 'geographical dispersion'
FXN_PA = 'peer analysis'
FXN_CP = 'company profile'
FXN_SINF = 'stock info'
FXN_SPFL = 'search profile'
FXN_PPL = 'people'
FXN_TV = 'tree view'
FXN_ITRG = 'investor targeting'
FXN_PSTD = 'perception study'
FXN_CSRV = 'create survey'
FXN_DE = 'disclosures enhancement'
FXN_WBC = 'webcasting'
FXN_ND = 'newswire distribution'
FXN_CN = 'create newswire'
FXN_OYD = 'order your documents'
FXN_MP = 'my projects'
FXN_P = 'projects'
FXN_F = 'files'
FXN_DB = 'dashboard'
FXN_ACM = 'announcements'
FXN_MCAL = 'my calendar'
FXN_C = 'contacts'
FXN_DL = 'distribution list'
FXN_NF = 'news feed'
FXN_DRAFTS = 'drafts'
FXN_OFM = 'open for meeting'
FXN_COPROF = 'co. profile'
FXN_SCR = 'screening'
FXN_SIA = 'sector & industry analysis'
FXN_FF = 'fund flow'
FXN_WEB = 'webinars'
FXN_SUR = 'surveys'
FXN_DESLAB = 'design lab'
FXN_SIA = 'sector & industry  analysis'
FXN_FF = 'fund flow'
FXN_WEB = 'webinars'
FXN_SUR = 'surveys'

FUNCTION_TYPES = [FXN_HM, FXN_FO, FXN_CS, FXN_FC, FXN_NWS, FXN_OV, FXN_EVT,
                  FXN_ST, FXN_DR, FXN_OV2, FXN_WC, FXN_DR2, FXN_UC, FXN_ST2,
                  FXN_OV3, FXN_WN, FXN_SVY, FXN_DR3, FXN_NW, FXN_IRM, FXN_CIR,
                  FXN_OCID, FXN_OTHER, FXN_AC, FXN_FL, FXN_CWEB, FXN_MN,
                  FXN_MC, FXN_SC, FXN_SP, FXN_SRQ, FXN_CRQ, FXN_CA, FXN_OFE,
                  FXN_AVL, FXN_CE, FXN_OA, FXN_S, FXN_BS, FXN_CO, FXN_H,
                  FXN_GD, FXN_PA, FXN_CP, FXN_SINF, FXN_SPFL, FXN_PPL, FXN_TV,
                  FXN_ITRG, FXN_PSTD, FXN_CSRV, FXN_DE, FXN_WBC, FXN_ND,
                  FXN_CN, FXN_OYD, FXN_MP, FXN_P, FXN_F, FXN_DB, FXN_ACM,
                  FXN_MCAL, FXN_C, FXN_DL, FXN_NF, FXN_DRAFTS, FXN_OFM,
                  FXN_COPROF, FXN_SCR, FXN_SIA, FXN_FF, FXN_WEB, FXN_SUR,
                  FXN_DESLAB]
# for direct use in model definition
FUNCTION_TYPES_CHOICES = [(v, v) for v in FUNCTION_TYPES]


# ticket statuses
TS_PG = 'pending'
TS_IP = 'in process'
TS_CD = 'closed'
STATUS_TYPES = [TS_PG, TS_IP, TS_CD]
# for direct use in model definition
STATUS_TYPES_CHOICES = [(v, v) for v in STATUS_TYPES]


# maximum length constraints
NAME_MAX_LENGTH = 128
EMAIL_MAX_LENGTH = 128
PHONE_MAX_LENGTH = 16
SUBJECT_MAX_LENGTH = 256
DES_MAX_LENGTH = 1024
