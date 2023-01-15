# 自作モジュール
import api
from models._setting import Base, DataBase

# 外部モジュール
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, desc, func, cast,select
from datetime import date, datetime, timedelta
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import relationship
from multiprocessing import Pool
from tqdm import tqdm
import multiprocessing
import sqlalchemy
import pandas as pd

# デバッグ用
import logging
from pprint import pprint as pp

logger = logging.getLogger(__name__)
class DocumentIndex(Base):
    """
    DocumentIndexes モデル\n
    有報のメタデータを格納する\n
    DateTime型のカラムにstrが入るとフォーマットに合わせて自動でDateあるいはDateTimeに変換される(要検証)\n

    以下 schema
    """
    __tablename__ = 'document_indexes'
    id =  Column('id', Integer, primary_key = True, autoincrement = True)
    edinet_code = Column('edinet_code', String(6))
    doc_id = Column('doc_id', String(8), unique = True)
    fund_code = Column('fund_code', String(6))  # ファンドコード
    ordinance_code = Column('ordinance_code', String(3))  # 府令コード
    form_code = Column('form_code', String(6))  #  様式コード
    doc_type_code = Column('doc_type_code', String(3))  #  書類種別コード
    period_start = Column('period_start', Date)  #  期間
    period_end =  Column('period_end', Date)
    submit_date_time = Column('submit_date_time', DateTime)  #  提出日時 YYYY-MM-DD 仕様書上はdateまでだが実際はdatetimeで保存可能
    doc_description = Column('doc_description', String(147))  #  表紙に表示される文字列
    issuer_edinet_code = Column('issuer_edinet_code', String(6))  #  大量保有について発行会社のEDINETコードが出力される
    subject_edinet_code = Column('subject_edinet_code',String(6))  #  公開買い付けについて対象となるEDINETコードが出力される
    subsidiary_edinet_code = Column('subsidiary_edinet_code', String(69))  #  子会社のEDINETコード
    current_report_reason = Column('current_report_reason', String(1000))  #  臨時提出事由
    parent_doc_id = Column('parent_doc_id', String(8))  #  親書類管理番号
    operated_date_time = Column('operated_date_time', DateTime)  #  操作日時 (財務局職員による修正・不開示日時)
    withdrawal_status = Column('withdrawal_status', String(1))  #  取り下げ区分
    doc_info_edit_status =  Column('doc_info_edit_status',String(1))  #  書類情報修正区分
    disclosure_status =  Column('disclosure_status',String(1))  #   不開示の場合を開始した場合１ すでに不開示の場合 2 解除の場合0か3
    xbrl_flag = Column('xbrl_flag',String(1))  #  XBRLがある場合は1
    pdf_flag = Column('pdf_flag', String(1))  #  PDFがある場合は1
    attach_doc_flag = Column('attach_doc_flag', String(1))  #  添付文書がある場合は1
    english_doc_flag = Column('english_doc_flag',String(1))  #   英文ファイルがある場合は1

    created_at = Column('created_at',DateTime,server_default=func.now())
    updated_at = Column('updated_at',DateTime,server_default=func.now(),onupdate=func.now())
    # リレーションは遅くなるので使用しないことにした
    # company = relationship('Company',back_populates="documents")

    '''
    以下クラスメソッド
    使用頻度が高く部品化されている度合いが高い順に並んでいる。
    '''

    @classmethod
    def dict_to_df(cls, data:dict) -> pd.DataFrame:
        '''
        DocumentIndexesテーブルのカラムに合わせてapiレスポンスデータを整形しリストで返す\n
        一番上流工程のメソッド\n
        '''
        records = pd.DataFrame()

        if data['metadata']['resultset']['count'] == 0:   #  有報が0件の場合
            return records

        for row in data['results']:
            records = pd.concat(records, pd.json_normalize(row))
        records.drop(columns=['seqNumber','secCode','filerName','JCN'], inplace=True)

        #  DBの命名規則にしたがってカラム名変更
        records.columns = ['doc_id',
                            'edinet_code',
                            'fund_code',
                            'ordinance_code',
                            'form_code',
                            'doc_type_code',
                            'period_start',
                            'period_end',
                            'submit_date_time',
                            'doc_description',
                            'issuer_edinet_code',
                            'subject_edinet_code',
                            'subsidiary_edinet_code',
                            'current_report_reason',
                            'parent_doc_id',
                            'operated_date_time',
                            'withdrawal_status',
                            'doc_info_edit_status',
                            'disclosure_status',
                            'xbrl_flag',
                            'pdf_flag',
                            'attach_doc_flag',
                            'english_doc_flag']
        # edinet_codeが空欄のdoc_idは空データなので取得しない
        records.dropna(subset=['edinet_code'], inplace=True)
        return records

    @classmethod
    def where(cls, session,column_name: object, query: str):
        '''
        カラム名(オブジェクト)を指定して検索ワードが一致する全てのレコードを返す
        '''
        records = session.query(cls).filter(column_name == query) .all()
        return records

    @classmethod
    def upsert(cls, data: pd.DataFrame):
        '''
        新規のレコードは保存し、primary_keyが重複したらupdateする。
        '''
        insert_stmt = insert(cls).values(data.to_dict(orient='records'))
        upsert_stmt = insert_stmt.on_duplicate_key_update(
                            doc_id=                 insert_stmt.inserted.doc_id,
                            edinet_code=            insert_stmt.inserted.edinet_code,
                            fund_code=              insert_stmt.inserted.fund_code,
                            ordinance_code=         insert_stmt.inserted.ordinance_code,
                            form_code=              insert_stmt.inserted.form_code,
                            doc_type_code=          insert_stmt.inserted.doc_type_code,
                            period_start=           insert_stmt.inserted.period_start,
                            period_end=             insert_stmt.inserted.period_end,
                            submit_date_time=       insert_stmt.inserted.submit_date_time,
                            doc_description=        insert_stmt.inserted.doc_description,
                            issuer_edinet_code=     insert_stmt.inserted.issuer_edinet_code,
                            subject_edinet_code=    insert_stmt.inserted.subject_edinet_code,
                            subsidiary_edinet_code= insert_stmt.inserted.subsidiary_edinet_code,
                            current_report_reason=  insert_stmt.inserted.current_report_reason,
                            parent_doc_id=          insert_stmt.inserted.parent_doc_id,
                            operated_date_time=     insert_stmt.inserted.operated_date_time,
                            withdrawal_status=      insert_stmt.inserted.withdrawal_status,
                            doc_info_edit_status=   insert_stmt.inserted.doc_info_edit_status,
                            disclosure_status=      insert_stmt.inserted.disclosure_status,
                            xbrl_flag=              insert_stmt.inserted.xbrl_flag,
                            pdf_flag=               insert_stmt.inserted.pdf_flag,
                            attach_doc_flag=        insert_stmt.inserted.attach_doc_flag,
                            english_doc_flag=       insert_stmt.inserted.english_doc_flag
                            )
        conn = DataBase.ENGINE.connect()
        conn.execute(upsert_stmt)

    @classmethod
    def upsert_a_record(cls, date=date.today(),days_before=0):
        '''
        一日分の有報を取得し、更新する\n
        日付を指定しないと本日の日付になる\n
        days_beforeにint型を渡すと整数日分前の有報を取得\n
        sessionは自動的に閉じられる\n
        '''
        date = date-timedelta(days_before)
        date_str = date.strftime('%Y-%m-%d')  #  strにフォーマット
        IndexList = api.get_document_metadata(date_str)
        arranged_data = cls.dict_to_df(IndexList)  #  整形

        if arranged_data.empty:  #  報告書が0件だった時の処理
            logger.info('本日提出された有価証券報告書はありません')
        else:
            try:
                cls.upsert(arranged_data)
                logger.info('%sの有報を保存完了',date_str)
            except sqlalchemy.exc.IntegrityError as e: #  すでに同じidの有報が保存されていた時の処理
                logger.info('%s',e)
                logger.info('%s 分の有報はidの重複によりDBに保存できませんでした。',date_str)

    @classmethod
    def upsert_5years_record(cls, years_before=5):
        '''
        edinetから取得できる全ての有報メタデータを取得する\n
        years_beforeを指定するとその年数分だけ実行する\n
        ただし、閏日に実行すると5年前の今日が存在せずエラーを起こす\n
        '''
        today = date.today()
        years_ago_today = date(today.year - years_before, today.month, today.day)  # n年前の今日の日付を返す
        # [1,2,...,756,..(n年前の今日と今日の差分)]
        num_list = range((today - years_ago_today).days)
        # 30日ずつ区切って並列処理に渡す
        step = 30
        num_list_separate = [num_list[start : start + step] for start in range(0, len(num_list), step)]
        cpu_num = multiprocessing.cpu_count()
        pool = Pool(processes=cpu_num)
        with tqdm(total=len(num_list_separate)) as t:
            for _ in pool.imap_unordered(bulk_upsert, num_list_separate):
                t.update(1)


    @classmethod
    def insert_from_latest_doc(cls):
        '''
        DBの最終更新日を取得し、その日から現在までの未取得の有報を取得する
        bulkではないので早くない
        '''
        session = DataBase.Session()
        # 最終
        latest_doc = session.query(DocumentIndex).order_by(desc(DocumentIndex.updated_at)).first()
        # datetime型からdate型に変換
        latest_date = latest_doc.updated_at.date()
        today = date.today()
        # 未取得の期間(日にち)をintで取得
        time_diff = abs((latest_date - today).days)
        for i in range(time_diff):
            cls.upsert_a_record(days_before=i)

    @classmethod
    def create_table(cls):
        Base.metadata.create_all(bind=DataBase.ENGINE,tables=[cls.__table__])

    @classmethod
    def drop_table(cls):
        Base.metadata.drop_all(bind=DataBase.ENGINE,tables=[cls.__table__])

def bulk_upsert(num_list):
    '''
    並列処理の中で使われる関数
    数字のリストを受け取り、その数字に対応する期間の有報をupsertする
    [0~29]を受け取ったら0~29日前の有報を一度に保存する
    '''
    bulk_df = pd.DataFrame()
    for i in num_list:
        today = date.today()
        itr_date = today - timedelta(i)
        date_str = itr_date.strftime('%Y-%m-%d')
        # 有報のメタデータのdictを取得
        meta_dict = api.get_document_metadata(date_str)
        # dictからDfに変換してdatabaseにupsertする単位に格納
        bulk_df = bulk_df.append(DocumentIndex.dict_to_df(meta_dict))

    # dfが空でなければ格納
    if not(bulk_df.empty):
        logger.info(str(bulk_df))
        DocumentIndex.upsert(bulk_df)