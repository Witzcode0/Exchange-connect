"""
Store some constants related to "roles"
"""

# user permissions values
EPT_AA = 'add account'
EPT_NU = 'add user'
EPT_AR = 'assign roles'
EPT_CR = 'create roles'
EPT_AM = 'assign menu items'
USER_PERMISSIONS = [EPT_AA, EPT_NU, EPT_AR, EPT_CR, EPT_AM]
# for direct use in model definition
USER_PERMISSIONS_CHOICES = [(v, v) for v in USER_PERMISSIONS]

# user default roles
ERT_SU = 'super admin'
ERT_AD = 'admin'
ERT_CA = 'client admin'
ERT_NO = 'normal'
ERT_MNG = 'account manager'
ERT_GUEST = 'guest'
ERT_DESIGN = 'designer'
ERT_ANALYST = 'analyst'
ROLES = [ERT_SU, ERT_AD, ERT_CA, ERT_NO, ERT_MNG, ERT_GUEST, ERT_DESIGN,
    ERT_ANALYST]
ADMN_ROLES = [ERT_SU, ERT_AD, ERT_CA, ERT_MNG]
# for direct use in model definition
ROLES_CHOICES = [(v, v) for v in ROLES]
# maximum length constraints
NAME_MAX_LENGTH = 128
