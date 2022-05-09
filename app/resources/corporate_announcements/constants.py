"""
Store some constants related to "corporate announcements"
"""

# category choices
CANNC_ANNUAL_REPORTS = 'annual reports'
CANNC_CONCAL_TRANSCRIPTS = 'concall transcripts'
CANNC_PRESENTATION = 'presentation'
CANNC_RESULT_UPDATES = 'result updates'
CANNC_NEWS = 'news'
CANNC_OTHERS = 'others'
CANNC_CATEGORY_TYPES = [CANNC_ANNUAL_REPORTS, CANNC_CONCAL_TRANSCRIPTS,
                        CANNC_PRESENTATION, CANNC_OTHERS, CANNC_RESULT_UPDATES,
                        CANNC_NEWS]
CANNC_CATEGORY_TYPES_CHOICES = [(v, v) for v in CANNC_CATEGORY_TYPES]

Sub_dict = {
    'Presentation' : CANNC_PRESENTATION,
    'Transcript' : CANNC_CONCAL_TRANSCRIPTS,
    'Annual Report' : CANNC_ANNUAL_REPORTS
}
Cat_dict = {
    'Result': CANNC_RESULT_UPDATES,
    'Outcome of Board Meeting' : CANNC_RESULT_UPDATES,
    'Annual Report' : CANNC_ANNUAL_REPORTS
}