import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
import requests

Base = declarative_base()
SECRETS = yaml.load(open('app/mysqlSecrets.yaml').read(),Loader=yaml.SafeLoader)
class DataBase(object):
    '''
    データベースの設定ファイル
    '''

    DATABASE = 'mysql://%s:%s@%s/%s?charset=utf8' % (
        'root',
        '',
        "localhost",
        'edinet_db',  # Do not change
    )

    ENGINE = create_engine(
        DATABASE,
        encoding = "utf-8",
        echo=True # Trueだと実行のたびにSQLが出力される
    )

    Session = scoped_session(
        sessionmaker(
            autocommit = False,
            autoflush = True,
            expire_on_commit = False,
            bind=ENGINE
        )
    )