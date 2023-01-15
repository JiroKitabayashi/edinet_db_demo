# 自作モジュールはこのファイルからはimportしない

# 外部モジュール
from os import error
import json
import pandas as pd
import re
from sqlalchemy.sql.expression import false, label, text

# デバッグ用
from pprint import pprint as pp
import logging
logger = logging.getLogger(__name__)

def text2words(text):
    '''
    文章を単語の配列で返す
    mecab.parseにしないとochasen2を指定しても半角スペースが削除されてしまう。
    '''
    mecab = MeCab.Tagger('-Ochasen2\
                        -d /usr/local/lib/mecab/dic/mecab-ipadic-neologd\
                        -u app/mecab/dic/edinet_db.dic')
    morphed_text = mecab.parse(text)
    # 末尾のEOSと開票を取り除く
    morphed_text = re.sub(r'\nEOS\n', '', morphed_text)
    word_data = morphed_text.split('\n')
    # 表層形の配列を返す
    words = [ i.split('\t')[0] for i in word_data]
    return words


def put_ibo2_tags():
    '''
    ラベル付きファイルからIBO2タグつきファイルを生成する。
    一時的に作ってしまったラベルファイルからIBOを合成するから鬼のスパゲッティコードになっている。
    '''
    df = pd.read_json('./tmp/data_set/admin.jsonl', orient='records', lines=True)
    text_column = df['data']
    label_column = df['label']
    tags_list = []
    for text, labels in zip(text_column,label_column):
        labels = sorted(labels)
        logger.info(f'text:{text}')
        logger.info(f'lablels{labels}')
        str_count = 0
        index = 0
        words = text2words(text)
        logger.info(f'words:{words}')
        ibo_tags = []
        try:
            for label in labels:
                label_head = label[0]
                label_end = label[1]
                label_str = label[2]
                for i in words:
                    # wordとlabelを適宜回すためにindex
                    word = re.sub(r'\\u3000', '　', words[index])
                    logger.info(f'word:{word}  word_len:{len(word)}')
                    if str_count == label_head:
                        if label_str == 'company_name':
                            ibo_tag = 'B-CompanyName'
                            logger.info(f'{word}:B-CompanyName')
                        elif label_str == 'position':
                            ibo_tag = 'B-Position'
                            logger.info(f'{word}:B-Position')
                        elif  label_str == 'start':
                            ibo_tag = 'B-Start'
                            logger.info(f'{word}:B-Start')
                        elif label_str == 'end':
                            ibo_tag = 'B-End'
                            logger.info(f'{word}:B-End')
                        elif label_str == 'transfer':
                            ibo_tag = 'B-Transfer'
                            logger.info(f'{word}:B-Transfer')
                        index += 1
                    elif label_end > str_count > label_head:
                        if label_str == 'company_name':
                            ibo_tag = 'I-CompanyName'
                            logger.info(f'{word}:I-CompanyName')
                        elif label_str == 'position':
                            ibo_tag = 'I-Position'
                            logger.info(f'{word}:I-Position')
                        elif  label_str == 'start':
                            ibo_tag = 'I-Start'
                            logger.info(f'{word}:I-Start')
                        elif label_str == 'end':
                            ibo_tag = 'I-End'
                            logger.info(f'{word}: I-End')
                        elif label_str == 'transfer':
                            ibo_tag = 'I-Transfer'
                            logger.info(f'{word}:I-Transfer')
                        index += 1
                    else:
                        ibo_tag = 'O'
                        logger.info(f'{word}: O')
                        index += 1
                    ibo_tags.append(ibo_tag)
                    str_count += len(word)
                    logger.info(f'str_count:{str_count} label_end:{label_end}')
                    # ラベルの終端がきたら次のラベルに行く
                    # ラベルが最後の場合でまだ単語が残っている場合は続ける
                    # 文の終端にきたら無条件で終わる
                    with open('tmp/data_set/data.txt', mode='a', encoding='utf-8') as f:
                        f.write(f'{word}\t{ibo_tag}\n')
                    if ((str_count == label_end) and not((label == labels[-1]) and index < len(words) )) or index == len(words):
                        logger.info(f'index:{index}, words_len:{len(words)}')
                        logger.info('break')
                        break
            logger.info(ibo_tags)
            tags_list.append(ibo_tags)
        except IndexError as e:
            pp(e)
            with open('tmp/morph_error.csv', mode='a', encoding='utf_8') as f:
                f.write(f'text:{text}\n')
                f.close
            val = input()

# data_setの下処理
def read_file(file_name):
    '''
    labelの開始・終了番号を用いてテキストを分割する。
    '''
    # データをdfに読み込む
    df = pd.read_json(file_name, orient='records', lines=True)
    texts_column = df['data']
    label_column = df['label']
    texts_list = []
    mappings = []
    for texts, labels in zip(texts_column,label_column):
        labels = sorted(labels)
        # テキストをラベルの区切りで分解したい
        splitted_texts = []
        offset_mappings = []
        # ラベルの先頭が0でない場合'O'をセットする
        if labels[0][0] != 0:
            splitted_texts.append(texts[:labels[0][0]])
            offset_mappings.append([0, labels[0][0], 'O'])
        for i, label in enumerate(labels):
            label_head = label[0]
            label_end = label[1]
            label_str = label[2]
            splitted_texts.append(texts[label_head:label_end])
            offset_mappings.append([label_head, label_end, label_str])
            # ラベルの間に隙間があったら0を埋める
            if not(label == labels[-1]):
                next_label = labels[i+1]
                if label_end != next_label[0]:
                    splitted_texts.append(texts[label_end:next_label[0]])
                    offset_mappings.append([label_end, next_label[0], 'O'])
        texts_list.append(splitted_texts)
        mappings.append(offset_mappings)
    return texts_list, mappings

# maps から IBO2タグを作る
# [CLS],[SEP],[PAD] は Garbageをふる
def encode_ibo2_tag(encoding, mappings):
    tags_list = []
    for map_sequence, enc in zip(mappings, encoding):
        str_count = 0
        ibo2_tags = []
        map_sequence = iter(map_sequence)
        map = next(map_sequence)
        for token in enc:
            if map:
                label_head = map[0]
                label_end = map[1]
                label_str = map[2]
                if token in ['[CLS]', '[SEP]','[PAD]']:
                        ibo_tag == 'Garbage'
                elif str_count == label_head:
                    if label_str == 'company_name':
                        ibo_tag = 'B-CompanyName'
                    elif label_str == 'position':
                        ibo_tag = 'B-Position'
                    elif  label_str == 'start':
                        ibo_tag = 'B-Start'
                    elif label_str == 'end':
                        ibo_tag = 'B-End'
                    elif label_str == 'transfer':
                        ibo_tag = 'B-Transfer'
                elif label_end > str_count > label_head:
                    if label_str == 'company_name':
                        ibo_tag = 'I-CompanyName'
                    elif label_str == 'position':
                        ibo_tag = 'I-Position'
                    elif  label_str == 'start':
                        ibo_tag = 'I-Start'
                    elif label_str == 'end':
                        ibo_tag = 'I-End'
                    elif label_str == 'transfer':
                        ibo_tag = 'I-Transfer'
                else:
                    ibo_tag = 'O'
                    ibo2_tags.append(ibo_tag)
                    str_count += len(token)
                # mapの終端とトークンの終端が一致したらきたら次のmapに行く
                if label_end == str_count:
                    try:
                        map = next(map_sequence)
                    except StopIteration:
                        map = None

    return tags_list




# 正規表現を用いた後株抽出も一応残しておく
def extract_company_name_ato(career_text) -> str:
    '''
    略歴文書から会社名を抽出する(後株)
    '''
    pattern = [
        '.+?(㈱|株式会社|㈲|有限会社)',  # 後株抽出 最短一致
        # 同社新日東事業所品質管理部長兼日本伸銅株式会社,同社新日東事業所品質管理部長兼日本伸銅株式会社特命執行役 （品質管掌）
        # 株式会社忠実屋（現株式会社,株式会社忠実屋（現株式会社ダイエー）入社
    ]
    # 後株抽出
    m = re.search(r'^(?![㈱|株式会社|㈲|有限会社])[^（）/(/)]+?(㈱|株式会社|㈲|有限会社)', career_text)