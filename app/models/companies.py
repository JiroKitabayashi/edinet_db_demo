from sqlalchemy import Column, Integer, String, Float, DateTime, func
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import validates, relationship
import pandas as pd
import urllib.request
import os
import zipfile
# 自作モジュール
from models._setting import DataBase, Base
# デバッグ用
from pprint import pprint as pp
class Company(Base):
    '''
    companiesModel\n
    データソース: javascript:EEW1E62071EdinetCodeListDownloadAction( 'lgKbn=2&dflg=0&iflg=0&dispKbn=1');

    https://disclosure.edinet-fsa.go.jp/E01EW/BLMainController.jsp?uji.bean=ee.bean.W1E62071.EEW1E62071Bean&uji.verb=W1E62071InitDisplay&TID=W1E62071&PID=W0EZ0001&SESSIONKEY=&lgKbn=2&dflg=0&iflg=0
    毎月更新される。
    '''
    __tablename__ = 'companies'
    id =  Column('id', Integer, primary_key = True, autoincrement = True)
    edinet_code = Column('edinet_code', String(6), unique=True)
    company_type = Column('company_type',String(25))
    listing_category = Column('listing_category',String(3))
    linking = Column('linking',String(1))
    capital = Column('capital', Float)
    closing_date = Column('closing_date',String(6))
    name = Column('name',String(128))
    name_english = Column('name_english',String(256))
    name_phonetic = Column('name_phonetic',String(256))
    location = Column('location',String(128))
    industry = Column('industry',String(32))
    sec_code = Column('sec_code', String(5))
    JCN = Column('JCN', String(13))  #  提出者法人番号
    market_infomation = Column('market_infomation', String(32))
    founding_date = Column('founding_date', DateTime)
    amount_of_sales = Column('amount_of_sales', String(9))
    number_of_consolidated_subsidiaries = Column('number_of_consolidated_subsidiaries', Integer)
    audit_company = Column('audit_company', String(32))
    main_bank = Column('main_bank', String(32))
    average_offficer_compensation = Column('average_officer_compensation', Integer)
    number_of_employees = Column('number_of_employees', Integer)
    number_of_auditor = Column('number_of_auditor', Integer)
    market_capitalization = Column('market_capitalization', Integer)
    net_asset = Column('net_asset', Integer)
    defined_number_of_director = Column('defined_number_of_director', Integer)
    defined_term_of_director = Column('defined_term_of_director', Integer)
    number_of_director = Column('number_of_director', Integer)
    number_of_outside_director = Column('number_of_outside_director', Integer)


    created_at = Column('created_at',DateTime,server_default=func.now())
    updated_at = Column('updated_at',DateTime,server_default=func.now(),onupdate=func.now())

    officers = relationship('OfficerCompany', back_populates='company')
    careers = relationship('Career', order_by="Career.name", back_populates="company")

    '''
    以下クラスメソッド
    部品化度合いが高い順に並んでいる
    '''

    @classmethod
    def download_edinet_code(cls):
        '''
        edinetに上場企業及び関連のある会社のCSVがあるのでそれをダウンロードしてくる
        '''
        url = 'https://disclosure.edinet-fsa.go.jp/E01EW/download?uji.verb=W1E62071EdinetCodeDownload&uji.bean=ee.bean.W1E62071.EEW1E62071Bean&TID=W1E62071&PID=W1E62071&SESSIONKEY=&downloadFileName=&lgKbn=2&dflg=0&iflg=0&dispKbn=1'
        file_path = 'tmp/EdinetcodeDlInfo.csv'
        zip_path = 'tmp/EDINET_CODE.zip'

        if os.path.exists(zip_path):
            os.remove(zip_path)
        # zipダウンロード
        urllib.request.urlretrieve(url, zip_path)

        # ディレクトリごと削除
        if os.path.exists(file_path):
            os.remove(file_path)

        # zip解凍
        with zipfile.ZipFile(zip_path) as existing_zip:
            existing_zip.extract('EdinetcodeDlInfo.csv','tmp')

    @classmethod
    def insertFromCSV(cls):
        '''
        edinet_code.csvを加工してcompaniesテーブルに追加する
        ＥＤＩＮＥＴコード,提出者種別,上場区分,連結の有無,資本金,決算日,提出者名,提出者名（英字）,提出者名（ヨミ）,所在地,提出者業種,証券コード,提出者法人番号
        '''
        edinet_codes = pd.read_csv('tmp/EdinetcodeDlInfo.csv',
                                    encoding='cp932',
                                    index_col='edinet_code',
                                    names=['edinet_code',
                                            'company_type',
                                            'listing_category',
                                            'linking',
                                            'capital',
                                            'closing_date',
                                            'name',
                                            'name_english',
                                            'name_phonetic',
                                            'location',
                                            'industry',
                                            'sec_code',
                                            'JCN'])  # cp932にしないとエラー
        edinet_codes.drop('ダウンロード実行日','ＥＤＩＮＥＴコード', inplace=True)
        edinet_codes.to_sql(name=cls.__tablename__, con=DataBase.ENGINE, if_exists='upsert',index=True)

    @classmethod
    def where(cls, session,column_name: object, query: str):
        '''
        カラム名(オブジェクト)を指定して検索ワードが一致する全てのレコードを返す
        '''
        records = session.query(cls).filter(column_name == query) .all()
        return records

    @classmethod
    def update_table(cls):
        # 会社情報CSVを更新
        cls.download_edinet_code()
        company_df = pd.read_csv('tmp/EdinetcodeDlInfo.csv',
                            encoding='cp932',
                            names=['edinet_code',
                                    'company_type',
                                    'listing_category',
                                    'linking',
                                    'capital',
                                    'closing_date',
                                    'name',
                                    'name_english',
                                    'name_phonetic',
                                    'location',
                                    'industry',
                                    'sec_code',
                                    'JCN'])
        company_df.drop([0,1], inplace=True)
        company_df = company_df.where(pd.notnull(company_df), None)

        insert_stmt = insert(Company).values(company_df.to_dict(orient='records'))
        on_duplicate_key_stmt = insert_stmt.on_duplicate_key_update(
            edinet_code =       insert_stmt.inserted.edinet_code,
            company_type =      insert_stmt.inserted.company_type,
            listing_category =  insert_stmt.inserted.listing_category,
            linking =           insert_stmt.inserted.linking,
            capital =           insert_stmt.inserted.capital,
            closing_date =      insert_stmt.inserted.closing_date,
            name =              insert_stmt.inserted.name,
            name_english =      insert_stmt.inserted.name_english,
            name_phonetic =     insert_stmt.inserted.name_phonetic,
            location =          insert_stmt.inserted.location,
            industry =          insert_stmt.inserted.industry,
            JCN =               insert_stmt.inserted.JCN
        )

        conn = DataBase.ENGINE.connect()
        conn.execute(on_duplicate_key_stmt)

    @classmethod
    def get_index(cls,session,name):
        '''
        おそらく使ってない
        '''
        records = cls.where(session,cls.name,name)
        return records[0].id

    @classmethod
    def create_table(cls):
        Base.metadata.create_all(bind=DataBase.ENGINE,tables=[cls.__table__])

    @classmethod
    def drop_table(cls):
        Base.metadata.drop_all(bind=DataBase.ENGINE,tables=[cls.__table__])
