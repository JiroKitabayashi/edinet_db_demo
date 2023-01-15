# 自作モジュール
from models._setting import Base, DataBase
from models.officers import Officer
from models.companies import Company
from models.careers import Career

# 外部モジュール
from sqlalchemy import Column, Integer, String, Float, DateTime, and_
from sqlalchemy.schema import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.dialects.mysql import insert
import pandas as pd

# デバッグ用
from pprint import pprint as pp

class OfficerCompany(Base):
    '''
    OfficerCompany Model
    '''
    __tablename__ = 'officers_companies'
    id = Column('id', Integer, primary_key = True, autoincrement = True)
    officer_id = Column('officer_id', Integer, ForeignKey('officers.id'))
    company_id = Column('company_id', Integer, ForeignKey('companies.id'))
    doc_id = Column('doc_id', String(8))
    position = Column('position',String(128))

    officer = relationship('Officer',back_populates='companies')
    company = relationship('Company',back_populates='officers')

    __table_args__ = (UniqueConstraint('officer_id','company_id'),)

    @classmethod
    def upsert(cls,data) -> None:
        insert_stmt = insert(cls).values(data.to_dict(orient='records'))
        upsert_stmt = insert_stmt.on_duplicate_key_update(
                        officer_id= insert_stmt.inserted.officer_id,
                        comapny_id=insert_stmt.inserted.company_id,
                        doc_id=insert_stmt.inserted.doc_id,
                        position=insert_stmt.inserted.position,
                        )
        conn = DataBase.ENGINE.connect()
        conn.execute(upsert_stmt)

    @classmethod
    def update_table(cls) -> None:
        '''
        OfficerCompanyテーブル全体を更新する
        '''
        session = DataBase.Session()
        result = session.query(Career, Officer, Company).\
            join(Officer, and_(Career.name == Officer.name,
                                Career.birthday == Officer.birthday)).\
            join(Company,Career.edinet_code == Company.edinet_code).all()

        officer_id = [i[1].id for i in result]
        company_id = [i[2].id for i in result]
        doc_id = [i[0].doc_id for i in result]
        position = [i[0].position for i in result]
        df = pd.DataFrame(
            {'officer_id':officer_id,
            'company_id':company_id,
            'doc_id':doc_id,
            'position':position
        })
        OfficerCompany.upsert(df)
        session.close()


    @classmethod
    def create_table(cls):
        Base.metadata.create_all(bind=DataBase.ENGINE,tables=[cls.__table__])

    @classmethod
    def drop_table(cls):
        Base.metadata.drop_all(bind=DataBase.ENGINE,tables=[cls.__table__])

if __name__ == "__main__":
    pass