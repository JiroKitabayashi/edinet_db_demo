import sqlalchemy
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Date, desc, func, cast,select
import pandas as pd
from datetime import date, datetime, timedelta
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import relationship
# 自作モジュール
import api
from models._setting import Base, DataBase
# デバッグ用
from pprint import pprint as pp

class DocumentBody(Base):
    """
    DocumentBodyモデル\n
    略歴文書のhtmlを格納する\n
    '有価証券報告書－第%'に該当する有報のみを取得する\n

    以下 schema
    """
    __tablename__ = 'document_body'
    id =  Column('id', Integer, primary_key = True, autoincrement = True)
    edinet_code = Column('edinet_code', String(6), unique = True)
    doc_id = Column('doc_id', String(8), unique = True)
    body = Column('body', Text, unique = True) # 無限長 str
    submit_date_time = Column('submit_date_time', DateTime)  #  提出日時 YYYY-MM-DD 仕様書上はdateまでだが実際はdatetimeで保存可能
    doc_description = Column('doc_description', String(147))  #  表紙に表示される文字列
    created_at = Column('created_at',DateTime,server_default=func.now())
    updated_at = Column('updated_at',DateTime,server_default=func.now(),onupdate=func.now())

    '''
    以下クラスメソッド
    使用頻度が高く部品化されている度合いが高い順に並んでいる。
    '''

    @classmethod
    def create_table(cls):
        Base.metadata.create_all(bind=DataBase.ENGINE,tables=[cls.__table__])

    @classmethod
    def drop_table(cls):
        Base.metadata.drop_all(bind=DataBase.ENGINE,tables=[cls.__table__])