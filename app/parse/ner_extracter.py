from models import careers
from api import bert_api
from pprint import pprint
import re

def extract_company_name(texts:list) -> object:
    '''
    略歴文書から会社名と役職を抽出する。\n
    [
        [{text: , words: , label: }]
    ]
    '''
    results = bert_api(texts)
    _list = []
    for text, res in zip(texts,results):
        words = []
        labels = []
        for i, r in enumerate(res):
            label = r['entity']
            word = re.sub('##', '', r['word'])
            score = r['score']
            if i == 0:
                words.append(word)
                labels.append(label)
            else:
                f_r = res[i-1]
                print(f_r)
                # 前のラベルと同じ場合は結合する
                if f_r['entity'] != r['entity']:
                    words.append(word)
                    labels.append(label)
                else:
                    words[-1] += word
        _list.append({'text': text, 'words':words, 'label':labels})
    return _list

