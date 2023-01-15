# -*- coding: utf-8 -*-
# 自作モジュール
from sqlalchemy.sql.expression import true
from api import api,yahoofinance
from models.careers import get_random_career
from parse import ner_extracter, parse
from models import *
from models import _helper
from mecab import *

# 外部モジュール
import pandas as pd
from sqlalchemy import desc, func
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
import multiprocessing
import datetime
import numpy
from dateutil import relativedelta
from time import sleep
import os
import glob
import re

# デバッグ用
import webbrowser
from pprint import pprint as pp
from tabulate import tabulate
import logging
# ログメッセージに時間を表示する
fmt = "%(asctime)s %(levelname)s %(name)s :%(message)s"
logging.basicConfig(level=logging.INFO, format=fmt)


'''
バックエンド側の実行ファイル
モデルにはそのモデルに対応するテーブルをCRUD操作するためのメソッドが存在し
datebase.pyで複数のモデル処理が必要な処理をする。
メソッドは部品化されている度合いが高い順に上から並んでいる。
'''


def check_parse_accuracy():
    '''
    parseのエラー率を検証する
    '''
    try_path = 'tmp/error_log/try_extract.csv'
    error_path = 'tmp/error_log/extract_error.csv'
    adjust_error_path = 'tmp/error_log/adjust_error.csv'
    if os.path.exists(try_path):
        os.remove(try_path)
    if os.path.exists(error_path):
        os.remove(error_path)
    if os.path.exists(adjust_error_path):
        os.remove(adjust_error_path)

    records = get_latest_docs()
    cpu_num = multiprocessing.cpu_count()
    pool = Pool(processes=cpu_num)
    with tqdm(total=len(records)) as t:
        for _ in pool.imap_unordered(check_parse_accuracy_process, records):
            t.update(1)


def check_parse_accuracy_process(record):
    '''
    check_parse_accuracy の並列化プロセス
    '''
    doc_id = record[1].doc_id
    with open('tmp/try_extract.csv', mode='a', encoding='utf_8_sig') as f:
        f.write(doc_id+'\n')
        f.close
    try:
        extracted_data = parse.extract_career_data_from_doc_id(doc_id)
        # print(extracted_data)
    except Exception as e:
        with open('tmp/extract_error.csv', mode='a', encoding='utf_8_sig') as f:
            f.write('%s;%s\n'%(doc_id,str(e).replace('\n',' ')))
            f.close
        return

    try:
        tabulate_print_career(doc_id,extracted_data)
    except Exception as e:
        with open('tmp/error_log/adjust_error.csv', mode='a', encoding='utf_8_sig') as f:
            f.write('%s;%s\n'%(doc_id,str(e).replace('\n','')))
            f.close
        return


def download():
    '''
    Careerの更新に必要なデータダウンロードを並列で行う
    '''
    records = get_latest_docs()
    cpu_num = multiprocessing.cpu_count()
    pool = Pool(processes=cpu_num)
    with tqdm(total=len(records)) as t:
        for _ in pool.imap_unordered(download_process, records):
            t.update(1)

def download_process(record):
    doc_id = record[1].doc_id
    filepath = "tmp/XBRL/"+doc_id
    if not os.path.exists(filepath):
        zippath = api.get_document(doc_id)
        filepath = parse.unzip(doc_id)
    else:
        print(doc_id +" xbrl exists")


def tabulate_print_career(doc_id,result="a"):
    edinet_code ="None"
    company_name = '当社'
    if type(result) == str:
        result = parse.extract_career_data_from_doc_id(doc_id)
    parse.adjust_str_format(result)
    # print(result)
    format_result = parse.format_extracted_data(result,doc_id,edinet_code,company_name)
    # print(format_result.head())
    format_result['date'] = format_result['date'].dt.strftime('%Y/%m')
    format_result['birthday'] = format_result['birthday'].dt.strftime('%Y/%m/%d')
    format_result = format_result.reindex(columns=['name', 'birthday', 'position','sub_position','date','description'])
    print(tabulate(format_result, headers='keys',
            tablefmt='simple',
            numalign='right',
            stralign='left', showindex=False))

def read_extract_error_csv():
    df = pd.read_csv("/tmp/extract_error.csv",sep=";",header=None,names=["doc_id","error"])
    return df

def read_adjust_error_csv():
    df = pd.read_csv("tmp/error_log/error_log/adjust_error.csv",sep=";",header=None,names=["doc_id","error"])
    return df

def tabulate_print_error_csv(df):
    print(tabulate(df.sort_values('error'), headers='keys',
            tablefmt='simple',
            numalign='right',
            stralign='left', showindex=False))

def scrape_debug():
    '''
    tmp/scdebug.csvからdoc_idを読み込み、順にextract_dataの一連の処理を実行する
    途中でパースしたhtmlをウェブブラウザで開く(必要ない場合はコメントアウト)
    try処理を使用していないため、エラー時にTracebackが出力される
    '''
    error_doc_ids = pd.read_csv("tmp/scdebug.csv",sep=";",header=None,names=["doc_id","error"])
    for doc_id in error_doc_ids["doc_id"]:
        edinet_xbrl_object = parse.get_xbrl_object(doc_id)
        officershtml = parse.get_officers_html(edinet_xbrl_object)
        officershtml_path = "tmp/HTML/"+doc_id+".html"
        with open(officershtml_path, mode='w', encoding="utf-8_sig") as f:
            f.write(officershtml)
        officershtml_url = "file://" + os.path.abspath(officershtml_path)

        #ウェブブラウザでhtmlを表示する処理
        # webbrowser.open_new_tab(officershtml_url)

        result = parse.extract_career_data(officershtml)
        result.to_csv("tmp/CSV/"+doc_id+".csv")
        tabulate_print_career(doc_id,result)

def get_dataset():
    '''
    学習にかけるためのデータセットを取得する関数
    直近5年の略歴データをランダムに5000件取得する。
    半角・全角スペースを削除
    ㈱ → （株）に変換する
    '''
    careers.get_random_career(num=10000)
    careers.trim_career_description()

if __name__ == '__main__':
    '''
    この中にメソット直書きしない
    '''
    _helper.update_entire_table()