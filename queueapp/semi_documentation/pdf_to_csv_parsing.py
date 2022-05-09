from bs4 import BeautifulSoup
import pandas as pd
import re
from tqdm import tqdm


class TextStyle(object):
    def __init__(self, class_name, font_size, font_family, color, bold,
                 is_bold, italic, is_italic, is_upper, has_link,
                 content, line_height, page_num, top_pos, left_pos):
        self.class_name = class_name
        self.font_size = font_size
        self.font_family = font_family
        self.color = color
        self.bold = bold
        self.is_bold = is_bold
        self.italic = italic
        self.is_italic = is_italic
        self.is_upper = is_upper
        self.has_link = has_link
        self.content = content
        self.line_height = line_height
        self.page_num = page_num
        self.top_pos = top_pos
        self.left_pos = left_pos

    # char_len = 0
    # word_len = len(self.content)

    def to_dict(self):
        return {
            'class_name': self.class_name,
            'font_size': self.font_size,
            'font_family': self.font_family,
            'color': self.color,
            'bold': self.bold,
            'is_bold': self.is_bold,
            'italic': self.italic,
            'is_italic': self.is_italic,
            'is_upper': self.is_upper,
            'has_link': self.has_link,
            'content': self.content,
            'line_height': self.line_height,
            'page_num': self.page_num,
            'top_pos': self.top_pos,
            'left_pos': self.left_pos
        }


class ClassStyle(object):
    def __init__(self, class_name, font_size, font_family, color,
                 line_height, page_num):
        self.class_name = class_name
        self.font_size = font_size
        self.font_family = font_family
        self.color = color
        self.line_height = line_height
        self.page_num = page_num

    def to_dict(self):
        return {
            'class_name': self.class_name,
            'font_size': self.font_size,
            'font_family': self.font_family,
            'color': self.color,
            'line_height': self.line_height,
            'page_num': self.page_num
        }


class PageWiseStatistic(object):
    def __init__(self, page_no, total_word, total_bold, total_link,
                 total_italic, total_upper, total_line):
        self.page_no1 = page_no
        self.total_word1 = total_word
        self.total_bold1 = total_bold
        self.total_link1 = total_link
        self.total_italic1 = total_italic
        self.total_upper1 = total_upper
        # self.total_paragraph = total_paragraph,
        self.total_line1 = total_line

    def to_dict(self):
        return {
            'page_no': self.page_no1,
            'total_word': self.total_word1,
            'total_link': self.total_link1,
            'total_bold': self.total_bold1,
            'total_italic': self.total_italic1,
            'total_upper': self.total_upper1,
            # 'total_paragraph': self.total_paragraph,
            'total_line': self.total_line1
        }


class FileWiseStatistic(object):
    def __init__(self, total_pages, total_word, total_bold, total_link,
                 total_italic, total_upper, total_paragraph, total_line):
        self.total_pages = total_pages,
        self.total_word = total_word,
        self.total_bold = total_bold,
        self.total_link = total_link,
        self.total_italic = total_italic,
        self.total_upper = total_upper,
        self.total_paragraph = total_paragraph,
        self.total_line = total_line

    def to_dict(self):
        return {
            'total_pages': self.total_pages,
            'total_word': self.total_word,
            'total_link': self.total_link,
            'total_italic': self.total_italic,
            'total_upper': self.total_upper,
            'total_paragraph': self.total_paragraph,
            'total_line': self.total_line
        }


def extract_text_style(path, p_tag):
    soup = BeautifulSoup(open(path), 'html.parser')
    clss = p_tag
    bold = False
    italic = False
    is_upper = False
    has_link = False
    line_height = 0
    is_bold = 0
    b_text = ''
    b_lenght = 0
    is_italic = 0
    i_lenght = 0
    i_text = ''

    parent_div = p_tag.fetchParents('div')[0]
    page_num = parent_div.get('id').split('page')[1].split("-")[0]

    class_name = clss.get('class')
    content = clss.get_text()
    if content.isupper():
        is_upper = True
    if clss.find_all('a'):
        has_link = True
    if clss.find_all('b'):
        for b in clss.find_all('b'):
            b_lenght += len(b.get_text())
            b_text = b_text.join(b.get_text())
            if b.get_text() == clss.get_text():
                bold = True
        if len(content) > 0:
            is_bold = round(b_lenght / len(content), 4)
        if b_text == clss.get_text():
                bold = True

    if clss.find_all('i'):
        for i in clss.find_all('i'):
            i_lenght += len(i.get_text())
            i_text = i_text.join(i.get_text())
            if i.get_text() == clss.get_text():
                italic = True
        if len(content) > 0:
            is_italic = round(i_lenght / len(content), 4)
        if i_text == clss.get_text():
                italic = True
    style_class = class_name[0]
    for style in soup.find_all('style'):
        if style_class in style.get_text():
            style_data = re.findall(r'(ft[0-9]*){(.*?)}', style.get_text())
            for sd in style_data:
                if sd[0] == style_class:
                    cls_style_data = sd[1]
                    font_size = re.search(r'font-size:(.*?);',
                                          cls_style_data).group(1)
                    font_family = re.search(r'font-family:(.*?);',
                                            cls_style_data).group(1)
                    color = re.search(r'color:(.*?);',
                                      cls_style_data).group(1)
                    try:
                        line_height = re.search(r'line-height:(.*?);',
                                                cls_style_data).group(1)
                    except AttributeError:
                            pass

    return TextStyle(class_name, font_size, font_family, color, bold,
                     is_bold, italic, is_italic, is_upper, has_link,
                     content, line_height, page_num)


# extracting style related data for each class attibute in <P> tag
def create_text_index(path, f_name, dataframe, df=False):
    with open(path) as f:
        soup = BeautifulSoup(f, 'html.parser')
    t_output = []
    page_stats_output = []
    file_stats_output = []
    class_dataframe = dataframe
    class_dataframe.set_index('class_name', inplace=True)

    # tqdm is used to see execution progress on terminal
    # as well as no. of iterations and execution time
    last_page_num = 0
    total_word = 0
    total_link = 0
    total_bold = 0
    total_italic = 0
    total_upper = 0
    total_paragraph = 0
    total_line = 0
    for p in soup.find_all('p'):
        is_upper = False
        has_link = False
        # ratio of lenght of bold tag text to length of total text
        is_bold = 0
        b_text = ''
        b_lenght = 0  # bold text length
        # ratio of lenght of italic tag text to length of total text
        is_italic = 0
        italic = False
        bold = False
        i_lenght = 0  # italic text length
        i_text = ''
        top_pos = 0
        left_pos = 0

        content = p.get_text().strip()
        if content.isupper():
            is_upper = True
        if p.find_all('a'):
            has_link = True

        if p.find_all('b'):
            for b in p.find_all('b'):
                b_lenght += len(b.get_text())
                b_text = b_text + b.get_text()
                if b.get_text().strip() == content:
                    bold = True
            if len(content) > 0:
                is_bold = round(b_lenght / len(content), 4)
            if b_text.strip() == content:
                bold = True

        if p.find_all('i'):
            for i in p.find_all('i'):
                i_lenght += len(i.get_text())
                i_text = i_text + i.get_text()
                if i.get_text().strip() == content:
                    italic = True
            if len(content) > 0:
                is_italic = round(i_lenght / len(content), 4)
            if i_text.strip() == content:
                italic = True
        # some p tags may be outside of the html tag in that case
        # its not able relate to parent div tag so we retaining
        # last page no for such p tags
        if p.fetchParents('div'):
            parent_div = p.fetchParents('div')[0]
            page_num = parent_div.get('id').split('page')[1].split("-")[0]
        else:
            page_num = page_num

        cn = p['class']  # cn is class name
        df_row = class_dataframe.loc[class_dataframe['page_num'] == page_num]
        df_row = df_row.loc[cn]
        font_size = df_row['font_size'].values[0]
        font_family = df_row['font_family'].values[0]
        color = df_row['color'].values[0]
        line_height = df_row['line_height'].values[0]

        style_attr = p['style']
        top_pos = re.search(r'.*?top:(.*?);', str(style_attr)).group(1)
        left_pos = re.search(r'.*?left:(.*?);', str(style_attr)).group(1)

        text_obj = TextStyle(cn, font_size, font_family,
                             color, bold, is_bold, italic, is_italic,
                             is_upper, has_link, content, line_height,
                             page_num, top_pos, left_pos)
        t_output.append(text_obj.to_dict())

        # for page wise statistics
        if last_page_num == page_num:
            total_word += len(content)
            if has_link:
                total_link += 1
            if is_bold:
                total_bold += 1
            if is_italic:
                total_italic += 1
            if is_upper:
                total_upper += 1
            total_line += 1
        else:
            page_obj = PageWiseStatistic(
                last_page_num, total_word, total_bold, total_link,
                total_italic, total_upper, total_line)
            page_stats_output.append(page_obj.to_dict())
            last_page_num = page_num
            total_word = len(content)
            if has_link:
                total_link = 1
            else:
                total_link = 0
            if is_bold:
                total_bold = 1
            else:
                total_bold = 0
            if is_italic:
                total_italic = 1
            else:
                total_italic = 0
            if is_upper:
                total_upper = 1
            else:
                total_upper = 0
            total_line = 1

        if df:
            pass
        else:
            print(text_obj.to_dict())

    dataf = pd.DataFrame(t_output)
    pagewisef = pd.DataFrame(page_stats_output)
    if df:
        dataf.to_csv(f_name + '_text_index.csv', sep='\t')
        pagewisef.to_csv(f_name + '_page_wise_stats.csv', sep='\t')


# extracting style related data for each <style> tag
def create_class_index(path, f_name, df=False):
    with open(path) as f:
        soup = BeautifulSoup(f, 'html.parser')
    c_output = []
    for html in tqdm(soup.find_all('html')):
        style_tag = html.head.style
        parent_div = html.body.div
        page_num = parent_div.get('id').split('page')[1].split("-")[0]

        # get style tag content in style_data
        style_data = re.findall(r'(ft[0-9]*){(.*?)}', style_tag.get_text())
        if not style_data:
            continue
        for sd in style_data:
            line_height = 0

            class_name = sd[0]
            cls_style_data = sd[1]
            font_size = re.search(r'font-size:(.*?);',
                                  cls_style_data).group(1)
            font_family = re.search(r'font-family:(.*?);',
                                    cls_style_data).group(1)
            color = re.search(r'color:(.*?);',
                              cls_style_data).group(1)
            try:
                line_height = re.search(r'line-height:(.*?);',
                                        cls_style_data).group(1)
            except AttributeError:
                            pass
            obj = ClassStyle(class_name, font_size, font_family,
                             color, line_height, page_num)
            c_output.append(obj.to_dict())
        if df:
            pass
        else:
            print(obj.to_dict())

    class_dataf = pd.DataFrame(c_output)
    if df:
        class_dataf.to_csv(f_name + '_class_index.csv', sep='\t')

    if class_dataf.empty:
        print('PDF is a scanned copy!!!!')
    else:
        # call text_index function and pass style related data as dataframe
        create_text_index(path, f_name, class_dataf, df)
