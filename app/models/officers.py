# 自作モジュール
from re import search
from models import careers
from models._setting import Base, DataBase
from models.careers import Career

# 外部モジュール
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, select, func, and_, update
from sqlalchemy.sql.expression import bindparam
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import relationship
import pandas as pd

# デバッグ用
from pprint import pprint as pp
class Officer(Base):
    """
    officer Model
    """
    __tablename__ = 'officers'
    id =  Column('id', Integer, primary_key=True, autoincrement = True)
    name = Column('name', String(64))
    birthday = Column('birthday', Date)
    created_at = Column('created_at',DateTime,server_default=func.now())
    updated_at = Column('updated_at',DateTime,server_default=func.now(),onupdate=func.now())

    companies = relationship('OfficerCompany', back_populates='officer')

    __table_args__ = (UniqueConstraint('name', 'birthday'),)

    @classmethod
    def upsert(cls, data:pd.DataFrame) -> None:
        insert_stmt = insert(cls).values(data.to_dict(orient='records'))
        upsert_stmt = insert_stmt.on_duplicate_key_update(
                        name = insert_stmt.inserted.name,
                        birthday= insert_stmt.inserted.birthday,
                    )
        conn = DataBase.ENGINE.connect()
        conn.execute(upsert_stmt)

    @classmethod
    def update_table(cls):
        '''
        officerテーブル全体を更新する
        '''
        session = DataBase.Session()
        records = Career.get_all(session)
        df = pd.DataFrame(records,columns=['name','birthday'])
        df = df.drop_duplicates(subset=['name','birthday'])
        cls.upsert(df)
        session.close()

    @classmethod
    def insert_officer_id_to_career(cls):
        '''
        careerテーブルを全取得して、officer_idを追加してupsertする。
        一度に全レコードupsertするとクラッシュするので
        1万行ずつ区切っている
        '''
        session = DataBase.Session()
        volume = session.query(Career).filter(Career.officer_id == None).count()
        session.close()
        for i in range(int(volume/10000) + 1): # +1で切り上げにしている
            session = DataBase.Session()
            records = [{
                                'id':career.id,
                                'date':career.date,
                                'name':career.name,
                                'birthday':career.birthday,
                                'doc_id':career.doc_id,
                                'edinet_code':career.edinet_code,
                                'officer_id':officer_id,
                                'description':career.description,
                                'position':career.position,
                                'sub_position':career.sub_position
                            }
                            for career, officer_id in session.query(Career,Officer.id).\
                            filter(Career.officer_id == None).\
                            outerjoin(Officer,and_(Career.name == Officer.name, Career.birthday == Officer.birthday)).\
                            limit(10000)
                        ]
            insert_stmt = insert(Career).values(records)
            upsert_stmt = insert_stmt.on_duplicate_key_update(
                            date= insert_stmt.inserted.date,
                            name= insert_stmt.inserted.name,
                            birthday=insert_stmt.inserted.birthday,
                            doc_id=insert_stmt.inserted.doc_id,
                            edinet_code=insert_stmt.inserted.edinet_code,
                            officer_id=insert_stmt.inserted.officer_id,
                            description=insert_stmt.inserted.description,
                            position=insert_stmt.inserted.position,
                            sub_position=insert_stmt.inserted.sub_position,
                            )
            conn = DataBase.ENGINE.connect()
            conn.execute(upsert_stmt)
            session.close()

    @classmethod
    def create_table(cls):
        Base.metadata.create_all(bind=DataBase.ENGINE,tables=[cls.__table__])

    @classmethod
    def drop_table(cls):
        Base.metadata.drop_all(bind=DataBase.ENGINE,tables=[cls.__table__])

    # デバック出力
    def __repr__(self):
        return "officers model<%s(id='%s', name='%s', birthday='%s')>" % (self.__tablename__, self.id, self.name, self.birthday)


