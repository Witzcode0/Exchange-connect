import re
from datetime import datetime
from io import BytesIO
import PyPDF2
import urllib.request
import io
import urllib3
import pdfplumber
import dateutil
from dateutil import parser
from app.common.helpers import time_converter

def extract_pdf_by_url(url):
    # http = urllib3.PoolManager()
    # temp = io.BytesIO()
    # temp.write(http.request("GET", url).data)
    req = urllib.request.Request(url, headers={'User-Agent': "Magic Browser"})
    remote_file = urllib.request.urlopen(req).read()
    remote_file_bytes = io.BytesIO(remote_file)
    all_text = ''
    try:
        with pdfplumber.open(remote_file_bytes) as pdf:
            for pdf_page in pdf.pages:
                single_page_text = pdf_page.extract_text()
                all_text = all_text + '\n' + single_page_text
        if all_text:
            textt = ' '.join(all_text.strip())
            revised = re.sub(r'\s+', '', textt)
            return revised
    except Exception as e:
        print(url, e)
        return 'False'


def get_text(url):
    text = ''
    wFile = urllib.request.Request(url)
    wFile.add_header('User-Agent',
                     'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36')
    res = urllib.request.urlopen(wFile)
    pdfReader = PyPDF2.pdf.PdfFileReader(BytesIO(res.read()), strict=False)
    no_of_pages = pdfReader.getNumPages()

    for each_page in range(no_of_pages):
        pageObj = pdfReader.getPage(each_page)
        temp = pageObj.extractText()
        text = text + temp

    revised = re.sub(r'\s+', '', text)

    return revised


def text_verification(text):
    keywords = ['financial performance', 'quarterly performance', 'earnings conference call', 'earnings call',
                'quarter ended', 'corporate performance', 'financial results', 'unaudited financial results',
                'un-audited', 'q1', 'q2', 'q3', 'q4']
    wrong_keywords = ['institutional meeting', 'institution meeting', 'one on one meeting', 'one-on-one',
                      'institutional investors meets', 'corporate day', 'interact with the investors',
                      'investors’ conference', 'investors conference', 'virtual', 'one on one', 'investorspresentation']
    import pdb
    # pdb.set_trace()
    yy = [''.join(x.split()) for x in keywords]
    xx = [''.join(x.split()) for x in wrong_keywords]
    if any(keyword in text.lower() for keyword in yy):
        if any(keyword in text.lower() for keyword in xx):
            return False,''
        else:
            if re.search(r'(?<=[0-9])(?:st|nd|rd|th)', text.lower()):
                rerevised = re.sub(r'(?<=[0-9])(?:st|nd|rd|th)', '', text.lower())
            else:
                rerevised = text.lower()
            return True, rerevised
    else:
        return False, ''


def get_concall_date(result, url):
    """
    Update concall date
    :param account_id: id of account
    """

    if result:
        pdf_text = extract_pdf_by_url(url)
        flag, processed_text = text_verification(pdf_text)
        if flag:
            #remove all spaces from string
            if re.search(r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)(\d{1,2})+([,]\d{4})', processed_text):
                result_dates = re.findall(r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)(\d{1,2})+([,]\d{4})', processed_text)
                lresult_dates = []
                for each in result_dates:
                    temp = ' '.join(x.capitalize() for x in each)
                    temp = re.sub(r'[^\w\s]', '', temp)
                    # temp = temp.capitalize()
                    lresult_dates.append(temp)
                dd = [dateutil.parser.parse(x) for x in lresult_dates]
                # d = [datetime.strptime(x, "%B %d %Y") for x in lresult_dates]
                youngest = max(dd)
                if youngest:
                    return youngest
                else:
                    print('No Dates: ', url)
                    return None

            elif re.search(r'(\d{1,2})(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)+([,]\d{4})', processed_text):
                result_dates = re.findall(r'(\d{1,2})(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)+([,]\d{4})', processed_text)

                lresult_dates = []
                for each in result_dates:
                    temp = ' '.join(x.capitalize() for x in each)
                    temp = re.sub(r'[^\w\s]', '', temp)
                    lresult_dates.append(temp)
                dd = [dateutil.parser.parse(x) for x in lresult_dates]
                # d = [datetime.strptime(x, "%d %B %Y") for x in lresult_dates]
                youngest = max(dd)
                if youngest:
                    return youngest
                else:
                    print('No Dates: ', url)
                    return None
            elif re.search(r'(\d{1,2})(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)+(\d{4})', processed_text):
                result_dates = re.findall(
                    r'(\d{1,2})(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)+(\d{4})',
                    processed_text)
                lresult_dates = []
                for each in result_dates:
                    temp = ' '.join(x.capitalize() for x in each)
                    temp = re.sub(r'[^\w\s]', '', temp)
                    lresult_dates.append(temp)

                dd = [dateutil.parser.parse(x) for x in lresult_dates]
                # d = [datetime.strptime(x, "%d %B %Y") for x in lresult_dates]
                youngest = max(dd)
                if youngest:
                    return youngest
                else:
                    print('No Dates: ', url)
                    return None
