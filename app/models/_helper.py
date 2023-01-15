from models import *
from mecab import mecab

from pandas.core.frame import DataFrame
from sqlalchemy.sql.expression import select
import pandas as pd
import re

# デバッグ
from pprint import pprint as pp

def update_entire_table():
    '''
    DocId
    Company
    Career
    Officer
    OfficerCompany
    の順にDBを更新し、DB全体を最新の状態にする。
    '''
    # DocIdテーブルを最終更新日を起点に更新
    DocumentIndex.upsert_5years_record()

    # Companyを更新(EDINET_CSVをダウンロード)
    Company.update_table()

    # Careerの更新
    # 直近１年分の有報を必要とするので結構時間がかかる
    Career.update_table()
    Officer.update_table()
    OfficerCompany.update_table()
    Officer.insert_officer_id_to_career()
    # officer_idが正しく挿入できているか確認
    check_career_officer_id()

def create_all():
    DocumentIndex.create_table()
    Company.create_table()
    Career.create_table()
    Officer.create_table()
    OfficerCompany.create_table()
    ManualInputCareer.create_table()

def drop_all():
    OfficerCompany.drop_table()
    Officer.drop_table()
    Career.drop_table()
    Company.drop_table()
    DocumentIndex.drop_table()

def check_career_officer_id():
    '''
    Careerテーブルのofficer_idが更新できているか確認する
    '''
    session = DataBase.Session()
    recs = session.query(Career).filter(Career.officer_id == None).all()
    if len(recs):
        raise Warning(str(len(recs)) + ' records have no officer_id')

def check_verb():
    '''
    サ変接続の名詞を取得する
    '''
    session = DataBase.Session()
    descriptions = session.query(Career.description).all()
    texts = [description[0] for description in descriptions]
    data =  mecab.morph_analysis(texts)
    sahen = []
    for text in data:
        for word in text:
            if 'サ変接続' in word['class']:
                sahen.append(word)
    df = pd.DataFrame(sahen)
    df = df.groupby('word').count()
    df = df.sort_values('class', ascending=False)
    df.to_csv('tmp/サ変接続名詞一覧.csv')

def maekabu_atokabu():
    '''
    前株と後株の割合を調べる
    '''
    session = DataBase.Session()
    comps = session.query(Company.name).all()
    maekabu = 0
    atokabu = 0
    others = []
    for comp in comps:
        name = comp.name
        if(re.search(r'^株式会社|^有限会社|^合同会社|^学校法人',name)):
            maekabu += 1
            print(name)
        elif(re.search(r'株式会社$|有限会社$|合同会社$|学校法人$',name)):
            atokabu += 1
        else:
            others.append(name)
    pp(others)
    print('前株： %i件、 後株: %i件, その他%i件', maekabu, atokabu, len(others))
