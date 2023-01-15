# 自作モジュール
from models import *
from controllers import _helper

# 外部モジュール
from flask import Blueprint, request, render_template
from flask import session as user_session # SQLのsessionと名前被りするため、user_sessionとする。
from flask_paginate import Pagination, get_page_parameter
from sqlalchemy import func, desc, not_

app = Blueprint('officer', __name__)



@app.route('/officer', methods=['GET'])
def index():
    '''
    役員データを所属会社とセットで返す
    records = [ {'officer':officer, 'companies':[ company, ..., ] }, ... ]
    '''
    db_session = DataBase.Session()
    company_name = request.args.get('company_name', None)
    officer_name = request.args.get('officer_name', None)

    current_page = request.args.get(get_page_parameter(), type=int, default=1)  # ページネーションの情報を取得
    per_page = 30

    # 後の検索で何回も使うquery
    base_query = db_session.query(Officer,func.group_concat(Company.name),func.group_concat(Company.edinet_code)).\
            outerjoin(OfficerCompany, Officer.id == OfficerCompany.officer_id).\
            outerjoin(Company, OfficerCompany.company_id == Company.id).\
            group_by(Officer.id).\
            order_by(Officer.name)

    # officer_nameとcompany_nameの両方存在する場合はand検索する
    if company_name and officer_name:
        records = base_query.\
            filter(Officer.name.like('%' + officer_name + '%')).\
            filter(Company.name.like('%' + company_name + '%')).\
            limit(per_page).offset((current_page-1) * per_page)
        # pagination用の検索結果総数を取得
        search_volume = base_query.\
            filter(Officer.name.like('%' + officer_name + '%')).\
            filter(Company.name.like('%' + company_name + '%')).count()
    elif (company_name and not(officer_name)):
        records = base_query.\
            filter(Company.name.like('%' + company_name + '%')).\
            limit(per_page).offset((current_page-1) * per_page)

        search_volume = base_query.\
            filter(Company.name.like('%' + company_name + '%')).\
            count()
    elif(officer_name and not(company_name)):
        records = base_query.\
                filter(Officer.name.like('%' + officer_name + '%')).\
                limit(per_page).offset((current_page-1) * per_page)

        search_volume = base_query.\
            filter(Officer.name.like('%' + officer_name + '%')).\
            count()
    else:
        # リクエストフォームは存在するが空欄の場合全てを返す
        records = base_query.limit(per_page).offset((current_page-1) * per_page)
        # pagination用の検索結果総数を取得
        search_volume = db_session.query(Officer).count()

    # 以下フロントに渡すためのデータ整形
    # func.grou_countは文字列をカンマ区切りで渡すため、リストに直す
    # [{'officer':Object,'companies':[{'company_name': name, 'edinet_code':code},...] }]の形にして渡す
    front_formated_data = []
    for rec in records.all():
        company_names = rec[1].split(',')
        edinet_codes = rec[2].split(',')
        company_data = [{'company_name':company_name, 'edinet_code':edinet_code} for company_name, edinet_code in zip(company_names, edinet_codes)]
        front_formated_data.append({'officer':rec[0],'company':company_data})

    # ページネーション処理
    page_disp_msg = '表示範囲 <b>{start}件 - {end}件 </b> 合計：<b>{total}</b>件'
    pagination = Pagination(page=current_page,
                            total=search_volume,
                            record_name='careers',
                            per_page=per_page,
                            css_framework='bootstrap4',
                            link_size='25',
                            display_msg=page_disp_msg)
    db_session.close()
    return render_template('officer/index.html',
                            records=front_formated_data,
                            company_name=company_name,
                            officer_name=officer_name,
                            pagination=pagination)

@app.route('/officer/<int:id>', methods=['GET'])
def show(id):
    db_session = DataBase.Session()
    # 所属会社を取得
    records = db_session.query(OfficerCompany,Company).\
        filter(OfficerCompany.officer_id == id).\
        outerjoin(Company, OfficerCompany.company_id == Company.id).\
        all()
    companies = [i[1] for i in records]
    careers = db_session.query(Career).filter(Career.officer_id == id).\
        order_by(Career.date).\
        all()
    print('--------------------------------------------')
    print(f'records:{records}')
    print('--------------------------------------------')

    db_session.close()
    return render_template('officer/show.html', companies=companies, careers=careers)
