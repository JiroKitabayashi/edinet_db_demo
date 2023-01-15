# 自作モジュール
from models._setting import DataBase, Base
from models.document_indexes import DocumentIndex, bulk_upsert
from models.companies import Company
import parse
import api

# 外部モジュール
import re
from sqlalchemy import Column, Integer, String, DateTime,Date, func, tuple_, select
from sqlalchemy.schema import ForeignKey
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import insert
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
from os import replace
from logging import Logger
from unicodedata import name
import multiprocessing
import time
import datetime
import pandas as pd
from collections import OrderedDict

# デバッグ用
import logging
from pprint import pprint as pp

logger = logging.getLogger(__name__)
class Career(Base):
    """
    career model
    DocumentIndex, Company, DocAPIがソース
    以下schema
    """
    __tablename__ = 'careers'
    id =  Column('id', Integer, primary_key = True, autoincrement = True)
    name = Column('name', String(64), nullable=False)
    birthday = Column('birthday', Date, nullable=False)
    doc_id = Column('doc_id',String(8))
    edinet_code = Column('edinet_code', String(6), ForeignKey('companies.edinet_code'))
    officer_id = Column('officer_id', Integer)
    position = Column('position',String(128), nullable=False)
    sub_position = Column('sub_position',String(128), nullable=True)
    date = Column('date', DateTime)
    description = Column('description', String(256))

    created_at = Column('created_at',DateTime,server_default=func.now())
    updated_at = Column('updated_at',DateTime,server_default=func.now(),onupdate=func.now())

    company = relationship('Company',back_populates="careers")

    __table_args__ = (UniqueConstraint('doc_id','description','date'),)



    @classmethod
    def get_all(cls, session):
        '''
        カラム名(オブジェクト)を指定して検索ワードが一致する全てのレコードを返す
        '''
        records = session.query(cls).with_entities(cls.name, cls.birthday)
        return records

    @classmethod
    def update_table(cls):
        '''
        Careerテーブル全体を更新する
        '''
        # 会社情報と直近の有報をjoinして取得
        records = get_latest_docs()
        # 100社ずつ区切って並列処理に渡す
        # step = 100
        # records_separate = [records[start : start + step] for start in range(0, len(records), step)]
        cpu_num = multiprocessing.cpu_count()
        pool = Pool(processes = cpu_num)
        with tqdm(total=len(records)) as t:
            for _ in pool.imap_unordered(update_process, records):
                t.update(1)


    @classmethod
    def upsert(cls, data: pd.DataFrame):
        insert_stmt = insert(cls).values(data.to_dict(orient='records',into=OrderedDict))
        upsert_stmt = insert_stmt.on_duplicate_key_update(
                        date= insert_stmt.inserted.date,
                        name= insert_stmt.inserted.name,
                        birthday=insert_stmt.inserted.birthday,
                        doc_id=insert_stmt.inserted.doc_id,
                        edinet_code=insert_stmt.inserted.edinet_code,
                        description=insert_stmt.inserted.description,
                        position=insert_stmt.inserted.position,
                        sub_position=insert_stmt.inserted.sub_position,
                        )
        conn = DataBase.ENGINE.connect()
        conn.execute(upsert_stmt)

    @classmethod
    def create_table(cls):
        Base.metadata.create_all(bind=DataBase.ENGINE,tables=[cls.__table__])

    @classmethod
    def drop_table(cls):
        Base.metadata.drop_all(bind=DataBase.ENGINE,tables=[cls.__table__])

'''
helper
'''

def get_latest_docs():
    '''
    全ての会社情報とその会社の直近の有報をjoinして取得\n
    Careerテーブルと直接やりとりはないのでクラスメソッドではない\n
    CompanyとDocumentIndexを参照するので直下のCareerに置いてある\n
    '''
    session = DataBase.Session()
    result = session.query(Company,DocumentIndex).\
        join(DocumentIndex, Company.edinet_code == DocumentIndex.edinet_code).\
            filter(
                tuple_(DocumentIndex.edinet_code,
                        DocumentIndex.submit_date_time).\
                in_(session.query(
                        DocumentIndex.edinet_code,
                        func.max(DocumentIndex.submit_date_time)
                    ).\
                    filter(
                        DocumentIndex.ordinance_code == '010',
                        DocumentIndex.form_code == '030000',
                        DocumentIndex.doc_type_code == '120').\
                    group_by(DocumentIndex.edinet_code)
                )
            ).\
            filter(
                DocumentIndex.ordinance_code == '010',
                DocumentIndex.form_code == '030000',
                DocumentIndex.doc_type_code == '120',
                Company.listing_category=='上場'
            ).all()
    session.close()
    return result

def update_process(record:list):
    '''
    record = get_latest_doc()\n
    並列処理で扱う用の関数\n
    データ整形とupsertを行う\n
    '''
    company = record[0]
    document = record[1]
    doc_id =  document.doc_id
    # documentから略歴データを抽出
    try:
        extracted_data = parse.extract_career_data_from_doc_id(doc_id)
        print(extracted_data)
    except Exception as e:
        with open('tmp/extract_error.csv', mode='a', encoding='utf_8_sig') as f:
            f.write('%s;%s\n' % (doc_id, str(e).replace('\n','')))
            f.close()
        return

    try:
        parse.adjust_str_format(extracted_data)
    except Exception as e:
        with open('tmp/error_log/adjust_error.csv', mode='a', encoding='utf_8_sig') as f:
            f.write('%s;%s\n' % (doc_id, str(e).replace('\n','')))
            f.close()
        return

    try:
        careers_df = parse.format_extracted_data(extracted_data,doc_id,company.edinet_code,company.name)
        Career.upsert(careers_df)
    except Exception as e:
        with open('tmp/format_error.csv', mode='a', encoding='utf_8_sig') as f:
            f.write('%s;%s\n' % (doc_id, str(e).replace('\n','')))
            f.close()
        return

def get_random_career(num=100, only_description=True) -> object:
    '''
    ランダムに100件略歴を取得する\n
    retrun DataFrame\n
    '''
    if only_description:
        s = select(Career.description).order_by(func.rand()).limit(num)
    else:
        s = select(Career).order_by(func.rand()).limit(num)
    conn = DataBase.ENGINE.connect()
    result = conn.execute(s)
    logger.info(result)
    records_df = pd.DataFrame(result, columns=['description'])
    records_df.to_csv('tmp/random_career.csv', index = False, header=['description',])
    return records_df

def trim_career_description():
    '''
    学習の際に㈱がtokenizerによって(株)に変換されるため文字数が合わなくなるのを回避する\n
    空白を消す理由思い出せない。\n
    '''
    df = pd.read_csv('tmp/random_career.csv')
    print(df)
    descriprions = df['description']
    # print(descriprions)
    trimed_desc = [d.replace('㈱', '（株）') for d in descriprions]
    trimed_desc = [d.replace('㈲', '（有）') for d in trimed_desc]
    trimed_desc = [d.replace('　', '') for d in trimed_desc]
    trimed_desc = [d.replace(' ', '') for d in trimed_desc]
    df = pd.DataFrame(trimed_desc)
    df.to_csv('tmp/data_set/career_data.csv', index = False, header = False)



