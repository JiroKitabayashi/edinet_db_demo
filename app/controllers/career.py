# 自作モジュール
import logging
from flask.helpers import url_for
from werkzeug.utils import redirect
from models import *
from controllers import _helper

# 外部モジュール
from flask import Blueprint, request, render_template
from flask import session as user_session # SQLのsessionと名前被りするため、user_sessionとする。
from flask_paginate import Pagination, get_page_parameter
from sqlalchemy import func, desc, not_

# デバッグ用
logger = logging.getLogger(__name__)

app = Blueprint('career', __name__)

@app.route('/career_top', methods=['GET'])
def top():
    db_session = DataBase.Session()
    search_volume = db_session.query(Career).count()
    db_session.close()
    return render_template('career/top.html',search_volume=search_volume)

@app.route('/career', methods=['GET'])
def index():
    career_description= request.args.get('career_description', None)
    position = request.args.get('position', None)
    current_page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 30

    db_session = DataBase.Session()
    if career_description and not position:
        careers = db_session.query(Career, Company.name).\
            filter(
                Career.description.like('%' + career_description + '%')
            ).outerjoin(Company, Career.edinet_code == Company.edinet_code).\
            limit(per_page).offset((current_page-1) * per_page)
        # pagination用の検索結果総数を取得
        search_volume = db_session.query(Career).\
            filter(
                Career.description.like('%' + career_description + '%')
            ).count()
    elif not career_description and position:
        careers = db_session.query(Career, Company.name).\
            filter(
                Career.position.like('%'+ position +'%')
            ).outerjoin(Company, Career.edinet_code == Company.edinet_code).\
            limit(per_page).offset((current_page-1) * per_page)
        # pagination用の検索結果総数を取得
        search_volume = db_session.query(Career).\
            filter(
                Career.position.like('%'+ position +'%')
            ).count()
    elif career_description and position:
        careers = db_session.query(Career, Company.name).\
            filter(
                Career.description.like('%' + career_description + '%'),
                Career.position.like('%'+ position +'%')
            ).\
            outerjoin(Company, Career.edinet_code == Company.edinet_code).\
            limit(per_page).offset((current_page-1) * per_page)
        # pagination用の検索結果総数を取得
        search_volume = db_session.query(Career).\
            filter(
                Career.description.like('%' + career_description + '%'),
                Career.position.like('%' + position + '%')
            ).count()
    else:
        return top()

    # ページネーション用変数
    current_page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 30
    page_disp_msg = '表示範囲 <b>{start}件 - {end}件 </b> 合計：<b>{total}</b>件'
    pagination = Pagination(page=current_page,
                            total=search_volume,
                            record_name='careers',
                            per_page=per_page,
                            css_framework='bootstrap4',
                            link_size='25',
                            display_msg=page_disp_msg)
    db_session.close()

    return render_template('career/index.html',
                            careers=careers,
                            pagination=pagination,
                            career_description=career_description,
                            position = position,
                            search_volume=search_volume)