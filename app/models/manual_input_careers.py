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
class ManualInputCareer(Base):
    """
    career model
    DocumentIndex, Company, DocAPIがソース
    以下schema
    """
    __tablename__ = 'manual_input_careers'
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

    __table_args__ = (UniqueConstraint('doc_id','description','date'),)



    @classmethod
    def get_all(cls, session):
        '''
        カラム名(オブジェクト)を指定して検索ワードが一致する全てのレコードを返す
        '''
        records = session.query(cls).with_entities(cls.name, cls.birthday)
        return records


    @classmethod
    def upsert(cls, data: pd.DataFrame):
        # insert_stmt = insert(cls).values(data.to_dict(orient='records'))
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

    @classmethod
    def exist_check(cls,doc_id):
        '''
        doc_idを元にManualInputCareersテーブルを検索し、ヒットした場合はデータを、しなかった場合はFalseを返す
        '''
        db_session = DataBase.Session()
        data = db_session.query(ManualInputCareer).\
            filter(ManualInputCareer.doc_id == doc_id).all()
        db_session.close()
        if len(data) != 0:
            return data
        else:
            return False

'''
helper
'''