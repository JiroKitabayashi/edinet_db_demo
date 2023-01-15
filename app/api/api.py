# 外部モジュール
from numpy import result_type
import requests
import json
import concurrent.futures as confu
from multiprocessing import Pool
import multiprocessing

# デバッグ用
import logging
logger = logging.getLogger(__name__)

# 一覧apiを叩いて報告書のメタデータを取得する
def get_document_metadata(date: str) -> dict:
    url='https://disclosure.edinet-fsa.go.jp/api/v1/documents.json'
    params={'date':date,'type':2}
    res=requests.get(url,params=params)
    res=res.text
    res=json.loads(res)
    logger.info('apiから%sの報告書を取得', date)
    return res

def get_document(doc_id: str) -> str:
    '''
    doc_idを受け取ってファイルをダウンロードしてパスを返す
    '''
    url='https://disclosure.edinet-fsa.go.jp/api/v1/documents/'+doc_id
    params={'type':1}
    logger.info('%s is now downloading', doc_id)
    res=requests.get(url,params=params)
    res.encoding = res.apparent_encoding

    # 出力ファイル名
    zippath ='tmp/ZIP/'+ doc_id + '.zip'

    # ファイルへ出力
    if res.status_code == 200:
        with open(zippath, 'wb') as f:
            for chunk in res.iter_content(chunk_size=1024):
                f.write(chunk)
        logger.info('%s has successfully downloaded', doc_id)
    else:
        logger.info('%sの取得に失敗 status: %s', doc_id,res.status_code)

    return zippath

def get_documents(doc_ids: list) -> None:
    '''
    ダウンロードしたいDoc_idのリストを受け取って全てダウンロードする。
    '''
    with Pool(processes=multiprocessing.cpu_count()) as pool:
            pool.map(get_document, doc_ids)

def bert_api(texts:list):
    '''
    textのリストを渡すとNERにかけて予測確率とラベルを返す。
    [
        [{
            'entity': 'Position',
            'score': 0.99962866, 'index': 1,
            'word': '取締役',
            'start': None,
            'end': None}
    ]
    '''
    url = 'http://118.241.147.100:80'
    texts_json = json.dumps(texts)
    params = {'texts': texts_json}
    res = requests.get(url, params=params)
    res.encoding = res.apparent_encoding
    result = json.loads(res.text)
    result_list = eval(result['test'])
    return result_list