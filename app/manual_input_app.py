# 自作モジュール
from models import *
from controllers import *
from parse import *

# 外部モジュール
from sqlalchemy import exc, event
from sqlalchemy.pool import Pool
from flask import Flask, send_from_directory,render_template,request
import secrets
import pandas as pd
import requests
from lxml import html
from collections import OrderedDict

# デバッグ用
from logging import error, raiseExceptions
import logging
# ログメッセージに時間を表示する
fmt = "%(asctime)s %(levelname)s %(name)s :%(message)s"
logging.basicConfig(level=logging.INFO, format=fmt)

# Init Flask app
app = Flask(__name__, template_folder="manual_input/templates")

# flask側のsessionwをuser_session, SQL側のsessionをdb_sessionとする。
secret = secrets.token_urlsafe(32)
app.secret_key = secret

ssurl1 = 'https://docs.google.com/spreadsheets/d/1gVgtt7sVn0VA8jsEUpCqzphUd_QaXcDufQdU04noIhQ/edit?rm=minimal&single=true&widget=true&headers=false#gid=0'
ss_api_url1 = 'https://script.google.com/macros/s/AKfycbxqMqsXicaEoycGBjp8XhnLV2vd5c1AHH-ON7qFXFohMoy6ZkHkp0K7hDRA-ND2VhEN/exec'
ssurl2 = 'https://docs.google.com/spreadsheets/d/1HcJ5a4PrCucJaDcuBpTLB8CaIT2ZDQBQeeSGXUVQcuo/edit?rm=minimal&single=true&widget=true&headers=false#gid=0'
ss_api_url2 = 'https://script.google.com/macros/s/AKfycbzTo1_h1qI_cjTitkHlnHKya-n1t8TpT1f1U2SxtUBR74AF876Z0hufB6MF0n2_Yid5/exec'
ssurl3 = 'https://docs.google.com/spreadsheets/d/1NpYMkthJWES08mX9vfbzVN0Vju2KnXwNOE5ph_0Dkm0/edit?rm=minimal&single=true&widget=true&headers=false#gid=0'
ss_api_url3 = 'https://script.google.com/macros/s/AKfycbw-fi4A_Es2Nnp6xpn42FCYIo9P52TidTuidTFpPBvyRkQ6rzQYVZty2yUvmQrl9T4e/exec'

# 使うスプレッドシートの設定
ssurl = ssurl1
ss_api_url = ss_api_url1

def read_debug_csv(error_doc_ids):
    for index, row in error_doc_ids.iterrows():
        edinet_xbrl_object = parse.get_xbrl_object(row['doc_id'])
        officershtml = parse.get_plain_officers_html(edinet_xbrl_object)
        error_doc_ids.at[index, 'html'] = officershtml
    return error_doc_ids.values.tolist()

def get_ss_data():
    res = requests.get(ss_api_url)
    df = pd.read_json(res.text)
    return df

def reset_ss():
    res = requests.post(ss_api_url)
    if res.status_code != 200:
        raise ValueError
    return None

def delete_first_doc_id_from_csv():
    error_doc_ids = pd.read_csv("tmp/scdebug.csv",sep="\t",header=None,names=["doc_id","error"])
    error_doc_ids = error_doc_ids.drop(0, axis=0)
    error_doc_ids.to_csv("tmp/scdebug.csv",sep="\t",header=False,index=False)
    error_doc_ids = pd.read_csv("tmp/scdebug.csv",sep="\t",header=None,names=["doc_id","error"])
    return error_doc_ids

def get_edinet_code_from_doc_id(doc_id):
    db_session = DataBase.Session()
    edinet_code = db_session.query(DocumentIndex).\
        filter(DocumentIndex.doc_id == doc_id).first().edinet_code
    db_session.close()
    return edinet_code

def get_company_name_from_edinet_code(edinet_code):
    db_session = DataBase.Session()
    company_name = db_session.query(Company).\
        filter(Company.edinet_code == edinet_code).first().name
    db_session.close()
    return company_name

def add_career_df(row,career_df):
    pattern = re.compile(r'.年.*月', re.MULTILINE)
    if len(pattern.findall(row['date'])) >= 2:
        if row['date'].count('\n') == row['description'].count('\n'):
            date_list = row['date'].split('\n')
            detail_list = row['description'].split('\n')
            date_i = 0
            for date in date_list:
                career_df =  career_df.append({'date':date,'detail':detail_list[date_i]},ignore_index=True)
                date_i += 1
        # elif len(re.findall(r'.{3}年.*月',row['date']))*2 == row['date'].count('\n'):
        #     # print("========================")
        #     date_detail_list = row['date'].split('\n')
        #     date_detail_i = 0
        #     date_list = []
        #     detail_list = []
        #     for date_detail in date_detail_list:
        #         if date_detail_i%2 == 0:
        #             date_list.append(date_detail)
        #         else:
        #             detail_list.append(date_detail)
        #         date_detail_i += 1
        #     date_i = 0
        #     for date in date_list:
        #         career_df =  career_df.append({'date':date,'detail':detail_list[date_i]},ignore_index=True)
        #         date_i += 1
        elif len(row['description']) == 0:
            date_detail_list = row['date'].split('\n')
            for date_detail in date_detail_list:
                if re.fullmatch(r'.*年.*月\s?',date_detail):
                    career_df =  career_df.append({'date':date_detail},ignore_index=True)
                elif re.match(r'^\s?.{1,4}年.*月',date_detail):
                    date = date_detail.split('月')[0] + '月'
                    detail = "".join(date_detail.split('月')[1:])
                    career_df =  career_df.append({'date':date,'detail':detail},ignore_index=True)
                else:
                    print(date_detail)
                    detail = career_df.at[len(career_df)-1,'detail']
                    if str(detail) == 'nan':
                        detail = ''
                    career_df.at[len(career_df)-1,'detail'] = detail + date_detail
        else:
            raise ValueError(f'改行数が間違っています。detail={row["description"]}')
    else:
        career_df =  career_df.append({'date':row['date'],'detail':row['description']},ignore_index=True)
    return career_df

def convert_df_format(df):
    df = df[(df['description'].str.len() >= 1) | (df['date'].str.len() >= 1)|(df['position'].str.len() >= 1)].reset_index(drop=True)
    if df.at[len(df)-1,'position'].strip() == '計' or df.at[len(df)-1,'position'].strip() == '合計':
        df = df[:-1]
    if df.at[0,'birthday'].strip().replace(" ","") == '生年月日':
        df = df[1:]
    result = pd.DataFrame(columns=['氏名', '生年月日', '略歴', '役名','職名'])
    career_df = pd.DataFrame(columns=['date', 'detail'])
    df = df.reset_index(drop=True)
    for i, row in df.iterrows():
        if len(re.findall(r'\s?生\s?年\s?月\s?日\s?',row['birthday'])) == 1:
            continue
        if len(row['date']) == 0 and len(row['description']) == 0 and (row['position'].strip() == '計' or row['position'].strip() == '合計'):
            continue
        if len(row['description'])*3 < len(row['date']):
            row['description'] = ""
        if len(row['description']) == 0:
            if len(re.findall(r'.*年.*月',row['date'])) == 1:
                date_detail_str =  row['date']
                row['date'] = date_detail_str.split('月')[0] + '月'
                row['description'] = "".join(date_detail_str.split('月')[1:])
            elif len(re.findall(r'.年.*月',row['date'])) == 0:
                row['description'] = row['date'] 
                row['date'] = ""

        if len(row['description']) == 0 and len(row['date']) == 0 and len(row['position']) != 0:
            result.at[len(result)-1,'役名'] = result.at[len(result)-1,'役名'] + '\t' + row['position']
        elif i == 0:
            career_df =  add_career_df(row,career_df)
            result = result.append({'氏名':row['name'],'生年月日':row['birthday'],'役名':row['position'],'職名':row['sub_position']},ignore_index=True)
        elif i == len(df)-1:
            if row['name'] != df.at[i-1,'name']:
                career_df = career_df.applymap(lambda s: str(s).strip().replace("\n\n","\t").replace("\n","\t") if s and type(s) == str else s)
                result.at[len(result)-1,'略歴'] = career_df.to_json()
                career_df = pd.DataFrame(columns=['date', 'detail'])
                career_df =  add_career_df(row,career_df)
                career_df = career_df.applymap(lambda s: str(s).strip().replace("\n\n","\t").replace("\n","\t") if s and type(s) == str else s)
                result = result.append({'氏名':row['name'],'生年月日':row['birthday'],'役名':row['position'],'職名':row['sub_position'],'略歴':career_df.to_json()},ignore_index=True)
            else:
                career_df =  add_career_df(row,career_df)
                career_df = career_df.applymap(lambda s: str(s).strip().replace("\n\n","\t").replace("\n","\t") if s and type(s) == str else s)
                result.at[len(result)-1,'略歴'] = career_df.to_json()
        elif row['name'] == df.at[i-1,'name'] or len(row['name']) == 0:
            if len(row['position']) != 0:
                result.at[len(result)-1,'役名'] = result.at[len(result)-1,'役名'] + '\t' + row['position']
            career_df =  add_career_df(row,career_df)
        else:
            career_df = career_df.applymap(lambda s: str(s).strip().replace("\n\n","\t").replace("\n","\t") if s and type(s) == str else s)
            result.at[len(result)-1,'略歴'] = career_df.to_json()
            result = result.append({'氏名':row['name'],'生年月日':row['birthday'],'役名':row['position'],'職名':row['sub_position']},ignore_index=True)
            career_df = pd.DataFrame(columns=['date', 'detail'])
            career_df =  add_career_df(row,career_df)
    result = result.applymap(lambda s: str(s).strip().replace("\n\n"," ").replace("\n"," ").replace("\t"," ").replace("+"," ") if s and type(s) == str else s)
    result = result.reset_index(drop=True)
    return result

def exist_check(doc_id):
    db_session = DataBase.Session()
    data = db_session.query(ManualInputCareer).\
        filter(ManualInputCareer.doc_id == doc_id).all()
    db_session.close()
    if len(data) != 0:
        raise ValueError("データが既に存在しています")
    else:
        return None

@app.route('/', methods=['GET','POST'])
def index():
    error_doc_ids = pd.read_csv("tmp/scdebug.csv",sep="\t",header=None,names=["doc_id","error"])
    first_doc_id = error_doc_ids.iloc[0]['doc_id']
    if request.method == 'GET':
        edinet_xbrl_object = parse.get_xbrl_object(first_doc_id)
        officershtml = parse.get_plain_officers_html(edinet_xbrl_object)
        pdf_url = 'https://moneyworld.jp/discl-pdf/edinet/'+ first_doc_id +'.pdf'
        return render_template('index.html',officershtml=officershtml,ssurl=ssurl, pdf_url=pdf_url)
    elif request.method == 'POST' and request.form.get('button') == 'confirm':
        df = get_ss_data()
        result = convert_df_format(df)
        parse.adjust_str_format(result)
        format = parse.format_extracted_data(result,first_doc_id,'edinet_code','当社')
        format = format.reindex(columns=['position','sub_position','name','birthday','date','description','doc_id','edinet_code'])
        df_html = format.to_html()
        check_text = ""
        try:
            dfcount = len(result)
            edinet_xbrl_object = parse.get_xbrl_object(first_doc_id)
            officershtml = parse.get_officers_html(edinet_xbrl_object)
            officerscount = count_officers(html.fromstring(officershtml))
            if dfcount == officerscount:
                check_text = f'役員数とデータ数が同じ({officerscount}人)です。'
            else:
                check_text = f'警告：役員数({officerscount}人)とデータ数({dfcount}人)が合っていません。'
        except Exception:
            check_text = '役員数を取得できませんでした'
        return render_template('confirm.html',table_html=df_html,check_text=check_text)
    elif request.method == 'POST' and request.form.get('button') == 'ok':
        print("ManualInputCareerテーブル重複確認中")
        exist_check(first_doc_id)
        print("データ取得中")
        df = get_ss_data()
        print("データ整形中")
        result = convert_df_format(df)
        parse.adjust_str_format(result)
        edinet_code = get_edinet_code_from_doc_id(first_doc_id)
        company_name = get_company_name_from_edinet_code(edinet_code)
        format = parse.format_extracted_data(result,first_doc_id,edinet_code,company_name)
        print(format)
        print("ManualInputCareerテーブル更新中")
        ManualInputCareer.upsert(format)
        # print("Careerテーブル更新中")
        # Career.upsert(format)
        print("スプレッドシートリセット中")
        reset_ss()
        error_doc_ids = delete_first_doc_id_from_csv()
        first_doc_id = error_doc_ids.iloc[0]['doc_id']
        edinet_xbrl_object = parse.get_xbrl_object(first_doc_id)
        officershtml = parse.get_plain_officers_html(edinet_xbrl_object)
        pdf_url = 'https://moneyworld.jp/discl-pdf/edinet/'+ first_doc_id +'.pdf'
        return render_template('index.html',officershtml=officershtml,ssurl=ssurl, pdf_url=pdf_url)

@app.route('/list', methods=['GET'])
def list():
    # db_session = DataBase.Session()
    doc_id = request.args.get('doc_id', default = error_doc_ids_list[0][0], type = str)
    doc_html = error_doc_ids[error_doc_ids['doc_id'] == doc_id]['html'].iloc[0]
    doc_error = error_doc_ids[error_doc_ids['doc_id'] == doc_id]['error'].iloc[0]
    return render_template('list.html',error_doc_ids=error_doc_ids_list,doc_html=doc_html)


if __name__ == '__main__':
    # error_doc_ids = pd.read_csv("tmp/scdebug.csv",sep="\t",header=None,names=["doc_id","error"])
    # error_doc_ids['html'] = ''
    # error_doc_ids_list = read_debug_csv(error_doc_ids)
    app.run(debug=True, host='0.0.0.0', port=80, threaded=True)