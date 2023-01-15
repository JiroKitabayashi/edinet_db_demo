# 自作モジュール
from pandas.core.reshape.concat import concat
from api import api

# 外部モジュール
from bs4 import BeautifulSoup
from edinet_xbrl.edinet_xbrl_parser import EdinetXbrlParser
from lxml import html
from lxml.etree import tostring
import json
import pandas as pd
import zipfile
import glob
import re
import zipfile
import datetime
import locale
import os
import numpy as np
import requests
import csv
import math

# デバッグモジュール
from pprint import pprint as pp
import logging
logger = logging.getLogger(__name__)

def extract_career_data_from_doc_id(doc_id:str):
    '''
    doc_idを受け取って、テーブルの更新に必要なデータを返す。
    '''

    edinet_xbrl_object = get_xbrl_object(doc_id)
    officershtml = get_officers_html(edinet_xbrl_object)

    with open("tmp/HTML/"+doc_id+".html", mode='w', encoding="utf-8_sig") as f:
        f.write(officershtml)
    result = extract_career_data(officershtml)
    result.to_csv("tmp/CSV/"+doc_id+".csv")
    return result

def unzip(doc_id: str) -> str:
    '''
    zipファイルを解凍して解凍後のファイルパスを返す。\n
    '''
    zippath = 'tmp/ZIP/'+doc_id+'.zip'
    logger.info(doc_id+'を解凍します。')
    filepath = 'tmp/XBRL/'+doc_id
    with zipfile.ZipFile(zippath) as existing_zip:
        existing_zip.extractall(filepath)
    return filepath

def find_xbrl(file_path:str) -> str:
    '''
    解凍後のファイルパスから.xbrlファイルを検索してパスを返す。\n
    無ければNoneを返す。\n
    '''
    xbrl_path = None
    public_doc_path = file_path + '/XBRL/PublicDoc/'
    xbrl_files = glob.glob(public_doc_path+'*.xbrl')
    if len(xbrl_files) == 1:
        xbrl_path = xbrl_files[0]
    elif len(xbrl_files) >= 2:
        logger.info("XBRLファイルが2つ以上存在します")
        raise FileNotFoundError

    return xbrl_path

def remove_attrs(soup, black_list=tuple()):
    for tag in soup.findAll(True):
        for attr in [attr for attr in tag.attrs if attr in black_list]:
            del tag[attr]
    return soup

def is_json(myjson):
    try:
        json.loads(myjson)
    except Exception:
        return False
    return True

def count_officers(load_html):
    malecount = 0
    femalecount = 0
    text_list = load_html.xpath("//*[not(preceding::table) and not(ancestor-or-self::table)]")
    text = ""
    for t in text_list:
        text += t.text_content()
    text = text.translate(str.maketrans({chr(0xFF01 + i): chr(0x21 + i) for i in range(94)})).replace("\n","")
    m = re.match(r'.*?男性?(?P<male>.*?)名.*?女性?(?P<female>.*?)名', text)
    male = m.group('male').strip()
    female = m.group('female').strip()
    if male.isdecimal():
        malecount = int(male)
    if female.isdecimal():
        femalecount = int(female)
    return malecount + femalecount

def get_xbrl_object(doc_id:str):
    parser = EdinetXbrlParser()
    filepath = "tmp/XBRL/"+doc_id
    if not os.path.exists(filepath):
        zippath = api.get_document(doc_id)  #  ZIPファイルのダウンロード
        filepath = unzip(doc_id)
    else:
        logger.info(doc_id +" xbrl exists")
    xbrlpath = find_xbrl(filepath)
    edinet_xbrl_object = parser.parse_file(xbrlpath)
    return edinet_xbrl_object

def get_officers_html(edinet_xbrl_object):
    key = "jpcrp_cor:InformationAboutOfficersTextBlock"
    context_ref = "FilingDateInstant"

    officershtml = edinet_xbrl_object.get_data_by_context_ref(key, context_ref).get_value()
    soup = BeautifulSoup(officershtml, "html5lib")
    soup = remove_attrs(soup, ("style",))
    soup.body.hidden = True
    return str(soup)

def get_plain_officers_html(edinet_xbrl_object):
    key = "jpcrp_cor:InformationAboutOfficersTextBlock"
    context_ref = "FilingDateInstant"

    officershtml = edinet_xbrl_object.get_data_by_context_ref(key, context_ref).get_value()
    return officershtml

def concat_detail_text(result):
    for i, r in result.iterrows():
        if is_json(r['略歴']) and re.search(r'.*月.*日',r["生年月日"]) != None:
            df = pd.read_json(r['略歴'])
            df.reset_index(drop=True, inplace=True)
            # print(df)
            for index, row in df.iterrows():
                if ''.join(str(row['date']).split()) == ''.join(str(row['detail']).split()) and type(row['detail']) == str:
                    if df.at[index - 1,'detail'] != '!deleted!':
                        df.at[index - 1,'detail'] = str(df.at[index - 1,'detail']) + '\t' + str(row['detail'])
                    else:
                        index_w = index - 2
                        while df.at[index_w,'detail'] == '!deleted!':
                            index_w = index_w - 1
                        df.at[index_w,'detail'] = str(df.at[index_w,'detail']) + '\t' + str(row['detail'])
                    df.at[index,'detail'] = '!deleted!'
            df = df[df['detail'] != '!deleted!']
            result.at[i,'略歴'] = df.to_json()
    return result

def make_checkdf(result):
    checkdf = pd.DataFrame(columns=result.columns)
    for index, row in result.iterrows():
        if type(row["生年月日"]) == str:
            # logger.info(row["生年月日"])
            if re.search(r'.*月.*日',row["生年月日"]) != None:
                checkdf = checkdf.append(row,ignore_index=True)
    checkdf.reset_index(drop=True, inplace=True)
    return checkdf

def extract_career_data(officershtml):
    load_html = html.fromstring(officershtml)
    officers_count = count_officers(load_html)
    # tables = load_html.xpath("//table//*[contains(text(),'生年月日')]/ancestor::table[not(preceding::table//*[text()='計']) and not(preceding::table//*[text()='合計'])]")
    tables = load_html.xpath("//table[not(ancestor::table) and not(preceding::*[contains(text(),'補欠監査役')]) and not(preceding::*[contains(text(),'補欠取締役')]) and not(preceding::*[contains(text(),'補欠の監査')]) and not(preceding::*[contains(text(),'業務執行体制')]) and not(preceding::*[contains(text(),'スキル・マトリックス')]) and not(preceding::*[contains(text(),'選任の件')]) and not(preceding::*[contains(text(),'出席状況')]) and not(preceding::*[contains(text(),'略歴は次の')]) and not(preceding::*[contains(text(),'執行役員制度')]) and not(preceding::*[contains(text(),'社外役員の状況')])]")
    concat_output = pd.DataFrame()
    table_in_table = 1
    share_title = load_html.xpath("(//table//*[contains(text(),'所有') or contains(text(),'所　有') or text()='株式数' or contains(text(),'株式数')]/ancestor::td)[1]")[0].text_content().strip().replace( '\n' , '' ).replace(' ','').replace('　','')
    for table_tag in tables:
        table_html_str = html.tostring(table_tag,method='html',encoding="utf-8").decode(encoding='utf-8')
        load_table_html = html.fromstring(table_html_str)
        td_elements = load_table_html.xpath('//tr/td[not(ancestor::td)]')
        table_in_table = len(load_table_html.xpath('//tr//tr'))
        column_names = load_table_html.xpath('//thead/tr/td')
        column_names = [x for x in column_names if len(x)]
        for content in td_elements:
            if len(table_elem_list := content.cssselect("table")) > 0:
                insert_table_df = pd.DataFrame(columns=["date","detail"])
                for table_element in table_elem_list:
                    table_html = (html.tostring(table_element,method='html',encoding="utf-8").decode(encoding='utf-8'))
                    # logger.info("-------------------")
                    # logger.info(table_html)
                    # logger.info("-------------------")
                    table_df_list = pd.read_html(table_html,flavor="html5lib")
                    table_df = pd.DataFrame()
                    if len(table_df_list) >= 1:
                        table_df = table_df_list[0]
                    else:
                        table_df = pd.DataFrame(columns=["date","detail"])
                        break
                    table_df.dropna(how='all',inplace=True)
                    table_df.rename(columns={0: 'date',1:'detail'},inplace=True)
                    table_df = table_df.reset_index(drop=True)
                    if len(table_df.columns) >= 3:
                        logger.info(table_df)
                        errormsg = "tabledflen:" + str(len(table_df.columns))
                        raise ValueError(errormsg)
                    if len(table_df[lambda df: table_df['date'].astype(str).str.len() >= 10]):
                        table_html = table_html.replace("<br>", "+").replace("<br />", "+").replace("</p><p", "+</p><p")
                        table_html = re.sub('</p>\s*?<p', '+</p><p', table_html)
                        table_df = pd.read_html(table_html,flavor="html5lib")[0]
                        table_df.dropna(how='all',inplace=True)
                        table_df.dropna(how='all', axis=1,inplace=True)
                        table_df.columns = range(table_df.shape[1])
                        table_df.rename(columns={0: 'date',1:'detail'},inplace=True)
                        table_df = table_df.reset_index(drop=True)
                        new_table_df = pd.DataFrame(columns=["date","detail"])
                        # logger.info(table_df)
                        if len(table_df.columns) == 1:
                            table_df["detail"] = None
                            for index, row in table_df.iterrows():
                                table_df_long_date_txt = row["date"]
                                table_df_long_date_pos = table_df_long_date_txt.find('月')
                                table_df.at[index, 'date'] = table_df_long_date_txt[:table_df_long_date_pos+1]
                                table_df.at[index, 'detail'] = table_df_long_date_txt[table_df_long_date_pos+1:]
                        for index, row in table_df.iterrows():
                            if type(row["date"]) == float:
                                if type(row["detail"]) == str:
                                    new_table_df.iloc[-1,1] += row["detail"]
                            elif len(row["date"]) >= 10:
                                date_list = str(row["date"]).strip().replace(u'\xa0', u'').split("+")
                                date_list = [x for x in date_list if len(x)]
                                for date in date_list:
                                    if len(date) >= 10:
                                        date_list = re.findall(".*?月", row["date"])
                                date_list = [n.replace("+","") for n in date_list]
                                detail_list = row["detail"].replace("+(","(").strip().split("+")
                                detail_list = [str(n).replace("\xa0","").replace("\u3000","") for n in detail_list]
                                detail_list = [x for x in detail_list if len(x)]
                                # logger.info(date_list)
                                # logger.info(detail_list)
                                if len(date_list) == len(detail_list):
                                    date_list_i = 0
                                    for l in date_list:
                                        new_table_df = new_table_df.append({"date":date_list[date_list_i],"detail":detail_list[date_list_i]},ignore_index=True)
                                        date_list_i += 1
                                elif len(date_list := str(row["date"]).strip().replace(u'\xa0', u'').split("+")) == len(detail_list):
                                    date_list_i = 0
                                    date_text = ""
                                    detail_text = ""
                                    for l in date_list:
                                        if len(l) and len(detail_text) == 0:
                                            detail_text = detail_list[date_list_i]
                                            date_text = date_list[date_list_i]
                                        elif len(l):
                                            new_table_df = new_table_df.append({"date":date_text,"detail":detail_text},ignore_index=True)
                                            detail_text = detail_list[date_list_i]
                                            date_text = date_list[date_list_i]
                                        else:
                                            detail_text += detail_list[date_list_i]
                                        date_list_i += 1
                                    new_table_df = new_table_df.append({"date":date_text,"detail":detail_text},ignore_index=True)
                                elif (date_list := list(filter(None, date_list)))  == len(detail_list):
                                    date_list_i = 0
                                    for l in date_list:
                                        new_table_df = new_table_df.append({"date":date_list[date_list_i],"detail":detail_list[date_list_i]},ignore_index=True)
                                        date_list_i += 1
                                # elif len(detail_list) / len(date_list) == 2:
                                #     new_detail_list = []
                                #     for d in range(len(detail_list/2)):
                                #         new_detail_list[d]= detail_list[d*2] + detail_list[d*2+1]
                                #     date_list_i = 0
                                #     for l in date_list:
                                #         new_table_df = new_table_df.append({"date":date_list[date_list_i],"detail":new_detail_list[date_list_i]},ignore_index=True)
                                #         date_list_i += 1
                                elif len(date_list) == 1:
                                    detail_text = ""
                                    for d in detail_list:
                                        detail_text += d
                                    new_table_df = new_table_df.append({"date":date_list[0],"detail":detail_text},ignore_index=True)
                                elif len(date_list) < len(detail_list) and len([x for x in detail_list if str(x).strip()[-1] == "・" or str(x).strip()[-1] == "、"]) > 0:
                                    new_detail_list = []
                                    new_detail_list_flag = False
                                    for d in range(len(detail_list)-1):
                                        if str(detail_list[d]).strip()[-1] == "・" or str(detail_list[d]).strip()[-1] == "、":
                                            new_detail_list_flag = True
                                        elif new_detail_list_flag:
                                            new_detail_list_flag = False
                                            new_detail_list.append(detail_list[d-1] + detail_list[d])
                                        else:
                                            new_detail_list.append(detail_list[d])
                                    if len(date_list) == len(new_detail_list):
                                        date_list_i = 0
                                        for l in date_list:
                                            new_table_df = new_table_df.append({"date":date_list[date_list_i],"detail":new_detail_list[date_list_i]},ignore_index=True)
                                            date_list_i += 1
                                elif len([a for a in date_list if len(a) >= 5]) == len(detail_list):
                                    date_list_i = 0
                                    new_date_list = [a for a in date_list if len(a) >= 5]
                                    for l in new_date_list:
                                        new_table_df = new_table_df.append({"date":new_date_list[date_list_i],"detail":detail_list[date_list_i]},ignore_index=True)
                                        date_list_i += 1
                                elif len(detail_list) - len(date_list) == 1 and (str(detail_list[-1]).strip()[0] == "(" or str(detail_list[-1]).strip()[0] == "（"):
                                    detail_list_last = detail_list[-1].strip()
                                    detail_list.pop(-1)
                                    detail_list[-1] = str(detail_list[-1]) + str(detail_list_last)
                                    date_list_i = 0
                                    for l in date_list:
                                        new_table_df = new_table_df.append({"date":date_list[date_list_i],"detail":detail_list[date_list_i]},ignore_index=True)
                                        date_list_i += 1
                                else:
                                    logger.info(len(date_list))
                                    logger.info(date_list)
                                    logger.info(len(detail_list))
                                    logger.info(detail_list)
                                    errormsg = "1datelen:" + str(len(date_list)) +",detaillen:" + str(len(detail_list)) + ",datelist:" + ",".join(date_list)  + ",detaillist:" + ",".join(detail_list)
                                    raise ValueError(errormsg)
                            else:
                                # logger.info(row)
                                # logger.info(new_table_df)
                                new_table_df = new_table_df.append({"date":row["date"].replace("+",""),"detail":row["detail"].replace("+","")}, ignore_index=True)
                        table_df = new_table_df
                    insert_table_df = insert_table_df.append(table_df,ignore_index=True)
                insert_table_df = insert_table_df.applymap(lambda s: str(s).strip() if s else s)
                table_elem_list[0].getparent().replace(table_elem_list[0],html.fromstring(insert_table_df.to_json()))
                if len(table_elem_list) >= 2:
                    table_elem_list.pop(0)
                    for table_elem in table_elem_list:
                        table_elem.getparent().replace(table_elem,html.fromstring("<div></div>"))
            elif table_in_table == 0: #S1007494パターン対応
                content_html = html.tostring(content,method='html',encoding="utf-8")
                content_html = content_html.decode(encoding='utf-8').replace("<br>", "+").replace("<br />", "+").replace("</p><p", "+</p><p")
                content_html = re.sub('</p>\s*?<p', '+</p><p', content_html)
                content.getparent().replace(content,html.fromstring(content_html))
        output = pd.read_html(html.tostring(load_table_html,method='html',encoding="utf-8").decode(encoding='utf-8'),flavor="html5lib")[0]

        # logger.info(output)
        # logger.info(share_title)
        # output.dropna(how='all',inplace=True)
        if table_in_table == 0:
            if column_names:
                column_list = []
                for column_name in column_names:
                    if column_name.text_content().strip() == "略歴":
                        column_list.append("日付")
                    column_list.append(column_name.text_content().strip())
                if len(output.columns) == len(column_list):
                    output.columns = column_list
                elif len(output.columns) == 8:
                    output.columns = ["役名","職名","氏名","生年月日","_日付","略歴","任期",share_title]
                    output = output.reset_index(drop=True)
                    output = output.reindex(output.index.drop(0))
                elif len(output.columns) == 7:
                    output.columns = ["役名","氏名","生年月日","_日付","略歴","任期",share_title]
                    output = output.reset_index(drop=True)
                    output = output.reindex(output.index.drop(0))
                elif len(output.columns) == 6:
                    output.insert(3, '_日付',output["略歴"])
                    output.columns = ["役名","氏名","生年月日","_日付","略歴","任期",share_title]
                    output = output.reset_index(drop=True)
                    output = output.reindex(output.index.drop(0))
            else: #S1007494パターン対応
                # logger.info(output)
                # logger.info("----------0----------")
                # logger.info(output.iloc[0])
                # logger.info("----------1----------")
                # logger.info(output.iloc[1])
                output_iloc0_trlist = []
                output_iloc1_trlist = []
                if len(output) == 1:
                    output = None
                else:
                    output_iloc0_trlist =  output.iloc[0].map(lambda s: str(s).strip().replace("\n"," ").replace("+"," ").replace(" ","").replace("　","").replace("(ふりがな)","") if s else s)
                    output_iloc1_trlist =  output.iloc[1].map(lambda s: str(s).strip().replace("\n"," ").replace("+"," ").replace(" ","").replace("　","").replace("(ふりがな)","") if s else s)
                if output is None:
                    pass
                elif "略歴" in list(output_iloc0_trlist):
                    output.columns = output_iloc0_trlist
                    output = output.reset_index(drop=True)
                    # logger.info(output)
                    output = output.reindex(output.index.drop(0))
                    # logger.info(output)
                elif "略歴" in list(output_iloc1_trlist):
                    output.columns = output_iloc1_trlist
                    output = output.reset_index(drop=True)
                    output = output.reindex(output.index.drop(1))
                    output = output.reset_index(drop=True)
                    output = output.reindex(output.index.drop(0))
                elif len(output.columns) == 8:
                    output.columns = ["役名","職名","氏名","生年月日","_日付","略歴","任期",share_title]
                    output = output.reset_index(drop=True)
                    output = output.reindex(output.index.drop(0))
                elif len(output.columns) == 7:
                    output.columns = ["役名","氏名","生年月日","_日付","略歴","任期",share_title]
                    output = output.reset_index(drop=True)
                    output = output.reindex(output.index.drop(0))
                elif len(output.columns) == 6:
                    if "略歴" in output.columns:
                        output.insert(3, '_日付',output["略歴"])
                        output = output.reset_index(drop=True)
                        output = output.reindex(output.index.drop(0))
                    else:
                        output.insert(3, '_日付',output[list(output.columns)[3]])
                    output.columns = ["役名","氏名","生年月日","_日付","略歴","任期",share_title]
                # output = output.reset_index(drop=True)
                # output = output.reindex(output.index.drop(0))
        else:
            output.dropna(how='all',inplace=True)
            if "略歴" in output.iloc[0].values:
                output.columns = output.iloc[0]
                output = output.reset_index(drop=True)
                output = output.reindex(output.index.drop(0))
            else:
                column_list = []
                for column_name in column_names:
                    column_list.append(column_name.text_content().strip())
                if len(output.columns) == len(column_list):
                    output.columns = column_list
                elif len(output.columns) == len(concat_output.columns):
                    output.columns = concat_output.columns
                elif len(output.columns) == 6:
                    output.insert(3, '_日付',output[list(output.columns)[3]])
                    output.columns = ["役名","氏名","生年月日","_日付","略歴","任期",share_title]
                else:
                    # logger.info(output)
                    # errormsg = "operror oplen:" + str(len(output.columns)) + ",opcol:" + ",".join([str(i) for i in list(output.columns)])
                    # raise ValueError(errormsg)
                    output = None

        if output is not None:
            output = output.loc[:,~output.columns.duplicated()]
            output.dropna(how='all',inplace=True)
            output = output.reset_index(drop=True)
            output.columns = output.columns.map(lambda s: str(s).strip().replace("\n"," ").replace("+"," ").replace(" ","").replace("　","").replace("(ふりがな)","") if s else s)
            if len(output.columns) == 6:
                output.insert(3, '_日付',output[list(output.columns)[3]])
                output.columns = ["役名","氏名","生年月日","_日付","略歴","任期",share_title]
                if is_json(output["_日付"][0]):
                    output = output.drop(columns=['_日付'])
            # logger.info(output)
            if "生年月日" in output.columns:
                # logger.info(output)
                if "生年月日" in output["生年月日"].iloc[0].strip().replace(" ",""):
                    output = output.reindex(output.index.drop(0))
                    output = output.reset_index(drop=True)
            # logger.info(concat_output)
            if len(concat_output) > 0:
                # if concat_output.tail(1)[concat_output.columns[0]].str.contains("計").bool() and concat_output.tail(1)[concat_output.columns[1]].str.contains("計").bool():
                if concat_output.tail(1)[concat_output.columns[0]].iloc[0] == concat_output.tail(1)[concat_output.columns[1]].iloc[0]:
                    logger.info(concat_output.tail(1))
                    logger.info("nn")
                # elif type(output[output.columns[0]].iloc[0]) != str:
                #     logger.info("aa")
                elif len(concat_output.columns) == len(output.columns) and concat_output.columns[-1] == output.columns[-1]:
                    output.columns = concat_output.columns
                    concat_output = pd.concat([concat_output,output])
                # elif len(concat_output.columns) - len(output.columns) == 1 and concat_output.[-1] == output.columns[-1]:
                #     logger.info("bb")
                elif len(concat_output.columns) - len(output.columns) >= 2:
                    logger.info("cc")
                else:
                    logger.info("dd")
                    logger.info(len(concat_output.columns) - len(output.columns))
                    logger.info(concat_output)
                    logger.info(output)
                    errormsg = "cccolen:" + str(len(concat_output.columns)) +",oplen:" + str(len(output.columns)) + ",cccol:" + ",".join([str(i) for i in list(concat_output.columns)]) + ",opcol:" + ",".join([str(i) for i in list(output.columns)])
                    raise ValueError(errormsg)
            elif len(output.columns) <= 4:
                pass
            elif not "生年月日" in output.columns:
                pass
            else:
                concat_output = pd.concat([concat_output,output])

    concat_output = concat_output.reset_index(drop=True)
    concat_output.to_csv("tmp/test.csv")
    if len(load_html.xpath('//tr//tr')) > 0 and not "_日付" in concat_output.columns:
        result = concat_output
    elif table_in_table == 0 and '日付' in concat_output.columns:
        if len(concat_output[lambda df: concat_output['日付'].str.len() >= 10]):
            new_concat_output = pd.DataFrame(columns=concat_output.columns)
            for index, row in concat_output.iterrows():
                if len(row["日付"]) >= 10:
                    date_list = str(row["日付"]).strip().replace(u'\xa0', u'').split("+")
                    date_list = [x for x in date_list if len(x)]
                    for date in date_list:
                        if len(date) >= 10:
                            date_list = re.findall(".*?月", row["日付"])
                    date_list = [n.replace("+","") for n in date_list]
                    detail_list = row["略歴"].replace("+(","(").strip().split("+")
                    detail_list = [x for x in detail_list if len(x)]
                    if len(date_list) == len(detail_list):
                        date_list_i = 0
                        series = row
                        for l in date_list:
                            series["日付"] = date_list[date_list_i]
                            series["略歴"] = detail_list[date_list_i]
                            new_concat_output = new_concat_output.append(series,ignore_index=True)
                            date_list_i += 1
                    elif len(date_list) == 1:
                        detail_text = ""
                        for d in detail_list:
                            detail_text += d
                        new_table_df = new_table_df.append({"date":date_list[0],"detail":detail_text},ignore_index=True)
                    else:
                        logger.info(len(date_list))
                        logger.info(date_list)
                        logger.info(len(detail_list))
                        logger.info(detail_list)
                        errormsg = "2datelen:" + str(len(date_list)) +",detaillen:" + str(len(detail_list)) + ",datelist:" + ",".join(date_list)  + ",detaillist:" + ",".join(detail_list)
                        raise ValueError(errormsg)
                else:
                    new_concat_output = new_concat_output.append(row, ignore_index=True)
            concat_output = new_concat_output
        result = concat_output.drop(columns=['日付'])
        result = result.drop_duplicates(subset='氏名',keep='last')
        result = result.reset_index(drop=True)
        for index, row in result.iterrows():
            if row['氏名'] != "計" and row['氏名'] != "合計" and row['氏名'] != "合　計" and type(row["氏名"]) == str and len(str(row["氏名"])) > 1 and len(str(row["生年月日"])) > 4:
                table_df = concat_output[concat_output['氏名'] == row['氏名']].loc[:,['日付','略歴']]
                table_df.columns = ["date","detail"]
                table_df = table_df.reset_index(drop=True)
                table_df = table_df.applymap(lambda s: str(s).strip() if s else s)
                result.at[index, '略歴'] = table_df.to_json()
    elif table_in_table == 0 or '_日付' in concat_output.columns: #S1007494パターン対応
        result = concat_output
        if '_日付' in concat_output.columns:
            result = concat_output.drop(columns=['_日付'])
        else:
            concat_output.insert(3, '_日付',concat_output["略歴"])
            concat_output.columns = ["役名","氏名","生年月日","_日付","略歴","任期",share_title]
            concat_output = concat_output.reset_index(drop=True)
            concat_output = concat_output.reindex()
            result = concat_output.drop(columns=['_日付'])
        result = result.drop_duplicates(subset='氏名',keep='last')
        result = result.reset_index(drop=True)
        # logger.info(concat_output)
        # logger.info(result)
        for index, row in result.iterrows():
            if row['氏名'] != "計" and row['氏名'] != "合計" and row['氏名'] != "合　計" and type(row["氏名"]) == str and len(str(row["氏名"])) > 1 and len(str(row["生年月日"])) > 4:
                table_df = concat_output[concat_output['氏名'] == row['氏名']].loc[:,['_日付','略歴']]
                to_json_df = pd.DataFrame(columns=["date","detail"])
                for index_t, row_t in table_df.iterrows():
                    if type(row_t["_日付"]) != str and len(re.findall(".*?月", row_t["略歴"])) > 0:
                        row_t["_日付"] = row_t["略歴"]
                    if len(str(row_t["_日付"])) >= 10:
                        date_list = str(row_t["_日付"]).strip().replace(u'\xa0', u'').split("+")
                        date_list = [x for x in date_list if len(x)]
                        detail_list = row_t["略歴"].replace("+(","(").strip().split("+")
                        detail_list = [x for x in detail_list if len(x)]
                        # logger.info(len(date_list))
                        # logger.info(date_list)
                        # logger.info(len(detail_list))
                        # logger.info(detail_list)
                        for date in date_list:
                            if len(date) >= 10:
                                date_list = re.findall(".*?月", row_t["_日付"])
                        for date in date_list:
                            if len(date) >= 10:
                                date_list = str(row_t["_日付"]).strip().replace(u'\xa0', u'').split("+")
                                date_list = [x for x in date_list if len(x)]
                        # logger.info(detail_list)
                        for date_list_i in range(len(date_list)):
                            if len(date_list[date_list_i]) >= 10:
                                date_text_list = re.findall(".*?月", date_list[date_list_i])
                                if date_text_list:
                                    date_list[date_list_i] = date_text_list[0]
                                elif date_list_i >= 1:
                                    if detail_list[date_list_i - 1]:
                                        detail_list[date_list_i - 1] = detail_list[date_list_i - 1] + date_list[date_list_i]
                                    else:
                                        date_list_before_i = date_list_i - 1
                                        while not detail_list[date_list_before_i]:
                                            date_list_before_i -= 1
                                        detail_list[date_list_before_i] = detail_list[date_list_before_i] + date_list[date_list_i]
                                    date_list[date_list_i] = None
                                    detail_list[date_list_i] = None
                        date_list = list(filter(None, date_list))
                        detail_list = list(filter(None, detail_list))
                        date_list = [n.replace("+","") for n in date_list]
                        if len(date_list) == len(detail_list):
                            date_list_i = 0
                            for l in date_list:
                                i_detail = None
                                if date_list[date_list_i] in detail_list[date_list_i]:
                                    i_detail = detail_list[date_list_i].replace(date_list[date_list_i],"")
                                else:
                                    i_detail = detail_list[date_list_i]
                                to_json_df = to_json_df.append({"date":date_list[date_list_i],"detail":i_detail},ignore_index=True)
                                date_list_i += 1
                        elif len(date_list) == 1:
                            detail_text = ""
                            for d in detail_list:
                                detail_text += d
                            to_json_df = to_json_df.append({"date":date_list[0],"detail":detail_text},ignore_index=True)
                        elif len(date_list) == 0 and len(detail_list) == 1 and is_json(detail_list[0]):
                            to_json_df = to_json_df.append(pd.read_json(detail_list[0]),ignore_index=True)
                        else:
                            logger.info(len(date_list))
                            logger.info(date_list)
                            logger.info(len(detail_list))
                            logger.info(detail_list)
                            errormsg = "3datelen:" + str(len(date_list)) +",detaillen:" + str(len(detail_list)) + ",datelist:" + ",".join(date_list)  + ",detaillist:" + ",".join(detail_list)
                            raise ValueError(errormsg)
                    else:
                        to_json_df = to_json_df.append({"date":str(row_t["_日付"]).replace("+",""),"detail":row_t["略歴"].replace("+","")},ignore_index=True)
                to_json_df = to_json_df.applymap(lambda s: str(s).strip() if s else s)
                for index_j, row_j in to_json_df.iterrows():
                    date_list_j = re.findall(".*?月", row_j["date"])
                    if type(row_j["date"]) != str:
                        to_json_df.at[index_j, 'date'] = None
                        to_json_df.at[index_j, 'detail'] = None
                    elif len(date_list_j) == 0:
                        date_list_j_y = re.findall(".*?年", row_j["date"])
                        if len(date_list_j_y) == 0:
                            to_json_df.at[index_j - 1, 'detail'] = str(to_json_df.at[index_j - 1, 'detail']) + str(row_j["date"]) + str(row_j["detail"])
                            to_json_df.at[index_j, 'date'] = None
                            to_json_df.at[index_j, 'detail'] = None
                        else:
                            date_list_j_y_detail = row_j["date"].replace(date_list_j_y[0],"")
                            to_json_df.at[index_j, 'date'] = date_list_j_y[0]
                            to_json_df.at[index_j, 'detail'] = date_list_j_y_detail
                to_json_df.dropna(inplace=True)
                result.at[index, '略歴'] = to_json_df.to_json()
                if type(row["役名"]) == str:
                    result.at[index, '役名'] = row["役名"].replace("+"," ")
                if "職名" in result.columns:
                    if type(row["職名"]) == str:
                        result.at[index, '職名'] = row["職名"].replace("+"," ")
                if type(row["氏名"]) == str:
                    result.at[index, '氏名'] = row["氏名"].replace("+","")
                if type(row["任期"]) == str:
                    result.at[index, '任期'] = row["任期"].replace("+","")
                # logger.info(row[share_title])
                result.at[index, share_title] = str(row[share_title]).replace("+","")
                # logger.info(to_json_df)


    else:
        result = concat_output
    result = result.applymap(lambda s: str(s).strip().replace("\n"," ").replace("+"," ") if s and type(s) == str else s)
    result.columns = result.columns.map(lambda s: str(s).strip().replace("\n"," ").replace("+"," ").replace(" ","").replace("　","").replace("(ふりがな)","") if s else s)

    #エラー検知部分
    if len(result.columns) > 7:
        errormsg = "longcolumn:" + str(len(result.columns)) +",columnlist:" + ",".join(result.columns)
        raise ValueError(errormsg)
    if len(result.columns) < 6:
        errormsg = "shortcolumn:" + str(len(result.columns)) +",columnlist:" + ",".join(result.columns)
        raise ValueError(errormsg)

    # logger.info(result)
    checkdf = make_checkdf(result)

    for index, row in checkdf.iterrows():
        # logger.info(row["略歴"])
        if is_json(row["略歴"]):
            career_checkdf = pd.read_json(row["略歴"])
            for index_c, row_c in career_checkdf.iterrows():
                check_date = row_c["date"]
                check_detail = row_c["detail"]
                # if len(str(check_date)) < 4 or len(str(check_date)) > 20:
                if len(str(check_date)) > 20:
                    result = concat_detail_text(result)
                    checkdf = make_checkdf(result)
                    # errormsg = "wrongdate:" + str(len(str(check_date))) + ",date:" + check_date + ",detail:" + check_detail
                    # raise ValueError(errormsg)
                if len(check_detail_re := re.findall(".*?年.*?月\s+", check_detail)) > 0:
                    if len(re.findall("[\[|(|（]\s*(明治|大正|昭和|平成|令和)?\s*[0-9０-９|同]+\s*年\s*[0-9０-９|同]+\s*月", check_detail)) == 0:
                        errormsg = "wrongdetail:" + str(len(check_detail_re)) + ",detail:" + check_detail + ",date:" + check_date
                        raise ValueError(errormsg)
        else:
            errormsg = "notjson:" + str(row["略歴"])
            raise ValueError(errormsg)
    # pp(checkdf)
    # logger.info("----------")
    # logger.info(checkdf)
    if len(checkdf) != officers_count:
        errormsg = "dfrowcount:" + str(len(checkdf)) + ",officers:" + str(officers_count) + ",dflist:" + ",".join(list(checkdf.iloc[:,0]))
        raise ValueError(errormsg)
    if "役職名" in checkdf.columns:
        if len(checkdf[checkdf["役職名"].isnull()]) > 0:
            errormsg = "nan役職名:" + str(len(checkdf[checkdf["役職名"].isnull()])) + ",dflist:" + ",".join(list(checkdf[checkdf["役職名"].isnull()]))
            raise ValueError(errormsg)
    if "役名" in checkdf.columns:
        if len(checkdf[checkdf["役名"].isnull()]) > 0:
            errormsg = "nan役名:" + str(len(checkdf[checkdf["役名"].isnull()])) + ",dflist:" + ",".join(list(checkdf[checkdf["役名"].isnull()]))
            raise ValueError(errormsg)
    if len(checkdf[checkdf["氏名"].isnull()]) > 0:
        errormsg = "nan氏名:" + str(len(checkdf[checkdf["氏名"].isnull()])) + ",dflist:" + ",".join(list(checkdf[checkdf["氏名"].isnull()]))
        raise ValueError(errormsg)
    if len(longnm := checkdf[lambda checkdf: checkdf['氏名'].str.len() >= 45]) > 0:
        errormsg = "long氏名:" + str(len(longnm)) + ",dflist:" + ",".join(list(longnm["氏名"]))
        raise ValueError(errormsg)
    if len(shortnm := checkdf[lambda checkdf: checkdf['氏名'].str.len() <= 1]) > 0:
        errormsg = "short氏名:" + str(len(shortnm)) + ",dflist:" + ",".join(list(shortnm["氏名"]))
        raise ValueError(errormsg)
    if len(checkdf[checkdf["生年月日"].isnull()]) > 0:
        errormsg = "nan生年月日:" + str(len(checkdf[checkdf["生年月日"].isnull()])) + ",dflist:" + ",".join(list(checkdf[checkdf["生年月日"].isnull()]))
        raise ValueError(errormsg)
    if len(longbd := checkdf[lambda checkdf: checkdf['生年月日'].str.len() >= 20]) > 0:
        errormsg = "long生年月日:" + str(len(longbd)) + ",dflist:" + ",".join(list(longbd["生年月日"]))
        raise ValueError(errormsg)
    if len(checkdf[checkdf["略歴"].isnull()]) > 0:
        errormsg = "nan略歴:" + str(len(checkdf[checkdf["略歴"].isnull()])) + ",dflist:" + ",".join(list(checkdf[checkdf["略歴"].isnull()]))
        raise ValueError(errormsg)
    # if len(checkdf[checkdf["任期"].isnull()]) > 0:
    #     errormsg = "nan任期:" + str(len(checkdf[checkdf["任期"].isnull()])) + ",dflist:" + ",".join(list(checkdf[checkdf["任期"].isnull()]))
    #     raise ValueError(errormsg)
    # if len(longtm := checkdf[lambda checkdf: checkdf['任期'].str.len() >= 20]) > 0:
    #     errormsg = "long任期:" + str(len(longtm)) + ",dflist:" + ",".join(list(longtm["任期"]))
    #     raise ValueError(errormsg)
    # if len(longst := checkdf[lambda checkdf: checkdf.iloc[:,-1].str.len() >= 20]) > 0:
    #     errormsg = "long株式数:" + str(len(longst)) + ",dflist:" + ",".join(list(longst.iloc[:,-1]))
    #     raise ValueError(errormsg)


    return result
    # (明\s?治\s?|大\s?正\s?|昭\s?和\s?|平\s?成\s?|令\s?和\s?)?[0-9０-９|同]+\s*年\s*[0-9０-９|同]+\s*月

def adjust_str_format(df:object) -> None:
    '''
    文字列のフォーマットを整える
    '''
    trans_table = str.maketrans({'１':'1', '２':'2', '３':'3', '４':'4', '５':'5', '６':'6', '７':'7', '８':'8', '９':'9', '０':'0'})
    locale.setlocale(locale.LC_TIME, 'ja_JP.UTF-8')  #  曜日表記を日本語に設定
    # logger.info(df)
    for i, row in enumerate(df['生年月日']):  #  元年表記未対応
        # logger.info(row)
        if type(row) == str:
            row = row.translate(trans_table) # 半角に修正
            row = re.sub(r'生','',row) # 生が末尾についてる場合削除
            row = re.sub(r'\s','',row) #  空白文字列全てを削除
            row = re.sub(r'(\(|\)|（|）)','',row)  # 半角 or 全角カッコを削除

            if re.search(r'.*月.*日',row) == None:
                # logger.info('生年月日のフォーマットに合わない文字列を削除 : '+row)
                df.drop(i, inplace=True)
                df.reset_index(drop=True, inplace=True)
                continue

            if '元' in row:
                row = re.sub(r'元','1',row)

            if '大正' in row:
                row = re.sub(r'^大正','',row)
                row = row.split('年')
                row[0] = str(int(row[0]) + 1868) + '年'
                row = ''.join(row)
            if '昭和' in row:
                row = re.sub(r'^昭和','',row)
                row = row.split('年')
                row[0] = str(int(row[0]) + 1925) + '年'
                row = ''.join(row)
            elif '平成' in row:
                row = re.sub(r'^平成','',row)
                row = row.split('年')
                row[0] = str(int(row[0]) + 1988) + '年'
                row = ''.join(row)
            elif '令和' in row:
                row = re.sub(r'^令和','',row)
                row = row.split('年')
                row[0] = str(int(row[0]) + 2018) + '年'
                row = ''.join(row)

            # バリデーションチェック
            if None == re.match(r'^\d{4}年([1-9]|1[0-2])月([1-9]|[1,2]\d|3[0,1])日$',row):
                # logger.info(row)
                errormsg = '生年月日の抽出に失敗しました。'
                raise ValueError(errormsg + " : " + str(row))

            df['生年月日'][i] = datetime.datetime.strptime(row,'%Y年%m月%d日')
        else:
            df.drop(i, inplace=True)
            df.reset_index(drop=True, inplace=True)


    for i, row in enumerate(df['氏名']):
        if str(row) == 'nan':
            raise ValueError("name is nan")
        
        officer_name_text = ''.join(row.split())
        officer_name_text = officer_name_text.translate(str.maketrans({chr(0xFF01 + i): chr(0x21 + i) for i in range(94)}))
        officer_name_text = re.sub(r'\(.+\)','',officer_name_text)  # 半角カッコに続く文字列を削除
        officer_name_text = re.sub(r'注\d+','',officer_name_text,1)
        officer_name_text = re.sub(r'\.?、?,?\s?\d*\s?\.?、?,?\s?\d*\s?$','',officer_name_text,5)
        officer_name_text = re.sub(r'\.?、?,?\s?\d*\s?\.?、?,?\s?\d*\s?$','',officer_name_text,5)
        officer_name_text = officer_name_text.replace("*","")

        df['氏名'][i] = officer_name_text

    if '役職名' in df.columns:
        for i, row in enumerate(df['役職名']):
            position_text = row
            position_text = position_text.translate(str.maketrans({chr(0xFF01 + i): chr(0x21 + i) for i in range(94)}))
            position_text = re.sub(r'\(\s?注\s?\d+\s?\)','',position_text,5)
            position_text = re.sub(r'\(\s?注\s?\)\s?\d+','',position_text,5)
            position_text = re.sub(r'\(注\)\s?\d+','',position_text,5)
            df['役職名'][i] = position_text
    elif ('役名' in df.columns) and not ('職名' in df.columns):
        for i, row in enumerate(df['役名']):
            position_text = row
            position_text = position_text.translate(str.maketrans({chr(0xFF01 + i): chr(0x21 + i) for i in range(94)}))
            position_text = re.sub(r'\(\s?注\s?\d+\s?\)','',position_text,5)
            position_text = re.sub(r'\(\s?注\s?\)\s?\d+','',position_text,5)
            position_text = re.sub(r'\(注\)\s?\d+','',position_text,5)
            df['役名'][i] = position_text
    elif ('役名' in df.columns) and ('職名' in df.columns):
        for i, row in enumerate(df['役名']):
            position_text = row
            position_text = position_text.translate(str.maketrans({chr(0xFF01 + i): chr(0x21 + i) for i in range(94)}))
            position_text = re.sub(r'\(\s?注\s?\d+\s?\)','',position_text,5)
            position_text = re.sub(r'\(\s?注\s?\)\s?\d+','',position_text,5)
            position_text = re.sub(r'\(注\)\s?\d+','',position_text,5)
            df['役名'][i] = position_text
        for i, row in enumerate(df['職名']):
            position_text = row
            position_text = position_text.translate(str.maketrans({chr(0xFF01 + i): chr(0x21 + i) for i in range(94)}))
            position_text = re.sub(r'\(\s?注\s?\d+\s?\)','',position_text,5)
            position_text = re.sub(r'\(\s?注\s?\)\s?\d+','',position_text,5)
            position_text = re.sub(r'\(注\)\s?\d+','',position_text,5)
            df['職名'][i] = position_text


    for i, career_json in enumerate(df['略歴']):
        career_df = pd.read_json(career_json)
        date = career_df['date']
        career_df.reset_index(inplace=True, drop=True)
        for j, row in enumerate(date):
            row = str(row).translate(trans_table) # 半角に変換
            row = ''.join(row.split()) #  空白文字列が含まれる場合削除
            # 略歴年が省略されている場合、一個前の略歴に追加する
            if str(row) == 'nan' or str(row) == '':
                row = date[(j-1)]
                if career_df['detail'][j-1] != '!deleted':
                    new_detail = str(career_df['detail'][j-1]) + '\t' + str(career_df['detail'][j])
                else:
                    errormsg = '日付空欄繰り上がり代入2回発生'
                    raise ValueError(errormsg)
                career_df['detail'][j-1] = new_detail
                career_df['detail'][j] = '!deleted!'

            if '同' == row or '〃' == row or '〃〃' == row or '同上' == row:
                row = date[j-1]
            elif '同年' in row:
                row = date[j-1].split('年')[0] +'年'+ row.split('年')[1]
            elif matchdate := re.fullmatch(r'[同|〃](?P<month>([1-9]|1[0-2]))月', row):
                row = date[j-1].split('年')[0] +'年'+ str(matchdate.group('month')) + '月'
            elif matchdate := re.fullmatch(r'[同|〃](?P<year>[0-9]?[0-9])([々〇〻\u3400-\u9FFF\uF900-\uFAFF]|[\uD840-\uD87F][\uDC00-\uDFFF])(?P<month>([1-9]|1[0-2]))月', row):
                if len(str(matchdate.group('year'))) == 2:
                    row = str(date[j-1].split('年')[0])[:2] + str(matchdate.group('year')) + '年'+ str(matchdate.group('month')) + '月'
                elif str(date[j-1])[:2] in ['大正','明治','昭和','平成','令和']:
                    row = str(date[j-1].split('年')[0])[:2] + str(matchdate.group('year')) + '年'+ str(matchdate.group('month')) + '月'
                else:
                    errormsg = '年度の形式が間違っています'
                    raise ValueError(errormsg)

            if '同月' in row:
                row = row.split('年')[0] +'年'+ date[j-1].split('年')[1]
            elif re.fullmatch(r'([1-9]|1[0-2])月', row):
                row = date[j-1].split('年')[0] +'年'+ row
            elif matchdate := re.fullmatch(r'(?P<year>[1-2][0|8|9][0-9]{2})([々〇〻\u3400-\u9FFF\uF900-\uFAFF]|[\uD840-\uD87F][\uDC00-\uDFFF])', row):
                row = str(matchdate.group('year')) + '年1月'
            elif matchdate := re.fullmatch(r'(?P<year>[1-2][0|8|9][0-9]{2})年度', row):
                row = str(matchdate.group('year')) + '年4月'
            
            career_df['date'][j] = row

        for j, row in enumerate(date):

            if '元' in row:
                row = re.sub(r'元','1',row)

            if '大正' in row:
                row = re.sub(r'^大正','',row)
                row = row.split('年')
                row[0] = str(int(row[0]) + 1868) + '年'
                row = ''.join(row)
            elif '昭和' in row:
                row = re.sub(r'^昭和','',row)
                row = row.split('年')
                row[0] = str(int(row[0]) + 1925) + '年'
                row = ''.join(row)
            elif '平成' in row:
                row = re.sub(r'^平成','',row)
                row = row.split('年')
                row[0] = str(int(row[0]) + 1988) + '年'
                row = ''.join(row)
            elif '令和' in row:
                row = re.sub(r'^令和','',row)
                row = row.split('年')
                row[0] = str(int(row[0]) + 2018) + '年'
                row = ''.join(row)

            row = row.translate(trans_table) # 半角に変換
            row = ''.join(row.split()) #  空白文字列が含まれる場合削除

            if re.fullmatch(r'[1-2][0|8|9][0-9]{2}年([0-9]|1[0-2])月', row):
                career_df['date'][j] = row
            elif matchdate := re.match(r'(?P<year>[1-2][0|8|9][0-9]{2})([々〇〻\u3400-\u9FFF\uF900-\uFAFF]|[\uD840-\uD87F][\uDC00-\uDFFF])(?P<month>([1-9]|1[0-2]))([々〇〻\u3400-\u9FFF\uF900-\uFAFF]|[\uD840-\uD87F][\uDC00-\uDFFF])', row):
                row = str(matchdate.group('year')) + "年" + str(matchdate.group('month')) + "月"
                career_df['date'][j] = row
            elif re.fullmatch(r'9999年([0-9]|1[0-2])月', row):
                career_df['date'][j] = row
            else:
                print(row)
                print(career_df['detail'][j])
                errormsg = f"date:{row} detail:{career_df['detail'][j]} backdate:{career_df['date'][j-1]} backdetail:{career_df['detail'][j-1]}"
                raise ValueError(errormsg)

        career_df = career_df[career_df['detail'] != '!deleted!']
        # career_df = career_df[~career_df['detail'].str.contains('!deleted!')]
        df['略歴'][i] = career_df.to_json()


def format_extracted_data(extracted_data,doc_id,edinet_code,company_name):
    trans_table = str.maketrans({'１':'1', '２':'2', '３':'3', '４':'4', '５':'5', '６':'6', '７':'7', '８':'8', '９':'9', '０':'0'})
    if '役職名' in extracted_data.columns:
        officers_data = extracted_data[['氏名', '生年月日', '略歴', '役職名']].copy()
        officers_data['職名'] = None
    elif ('役名' in extracted_data.columns) and not ('職名' in extracted_data.columns):
        officers_data = extracted_data[['氏名', '生年月日', '略歴', '役名']].copy()
        officers_data['職名'] = None
    elif ('役名' in extracted_data.columns) and ('職名' in extracted_data.columns):
        officers_data = extracted_data[['氏名', '生年月日', '略歴', '役名','職名']].copy()
    else:
        errormsg = 'カラムのパターンが想定外です。'
        raise ValueError(errormsg + " : " + str(extracted_data.columns))
    officers_data.columns =['name','birthday','career','position','sub_position']
    format_extracted_data_df = pd.DataFrame()   # bulk_insertするための箱
    for i, row in officers_data.iterrows():
        career_df = pd.read_json(row['career'])
        # Careerの更新
        for j, career_row in career_df.iterrows():
            # 「当社」の文字列を社名に置き換える
            if type(career_row['detail']) != str:
                raise ValueError(f'detailtypeerror: date={career_row["date"]}')
            career_row['detail'] = re.sub(r'(当社|弊社)', company_name, career_row['detail'])
            career_row['date'] = datetime.datetime.strptime(career_row['date'].translate(trans_table),'%Y年%m月')
            career_dict = {'date':[career_row['date']],
                            'name':[row['name']],
                            'birthday':[row['birthday']],
                            'doc_id':[doc_id],
                            'edinet_code':[edinet_code],
                            'description':[career_row['detail']],
                            'position':[row['position']],
                            'sub_position':[row['sub_position']],
                            }
            format_extracted_data_df = format_extracted_data_df.append(pd.DataFrame.from_dict(career_dict),ignore_index=True)
    return format_extracted_data_df

if __name__ == "__main__":
    logger.info(__name__)
    pass

# \s*[\(|（|\[|＜|\<|〔|「|『]?他?の?[主|重]?要?な?(法人|会社)?等?の?(兼職|兼務|代表状況)の?(状況)?[\)|）|\]|＞|>|〕|」|』]?\s*