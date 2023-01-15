# 自作モジュール
from models import *
from controllers import _helper

# 外部モジュール
from flask import Blueprint, request, render_template
from flask import session as user_session # SQLのsessionと名前被りするため、user_sessionとする。
from flask_paginate import Pagination, get_page_parameter
from sqlalchemy import func, desc, not_

app = Blueprint('company', __name__)



@app.route('/', methods=['GET', 'POST'])
def index():
    '''
    会社検索ページ
    '''
    db_session = DataBase.Session()
    # navi-barのリンクから飛んできた場合,前のページのフォームデータを削除
    _helper.form_clear()
    # 産業の一覧を取得
    industries = db_session.query(Company.industry,func.count(Company.industry)).\
        filter(Company.listing_category == "上場").\
        group_by(Company.industry).\
        order_by(desc(func.count(Company.industry))).all()
    # デフォルトでサービス業の会社を表示する
    industry = request.args.get('industry', default = "サービス業", type = str)
    current_page = request.args.get(get_page_parameter(), type=int, default=1) # ページネーションにおける現在のページ番号
    per_page = 30 # 1ページあたりの表示件数
    # 会社名検索のデフォルトはNone
    company_name = None
    # POSTリクエストのみsessionに検索条件を保存する
    if request.method == 'POST':
        user_session['request_form'] = request.form
    #  sessionからrequest_formを取得する。存在しない場合はNoneを返す
    request.form = user_session.get('request_form')

    if request.form:
        company_name = request.form.get('company_name') if request.form.get('company_name') else None
        if company_name:
            companies = db_session.query(Company).\
                filter(
                    Company.name.like('%' + company_name + '%'),\
                    Company.listing_category == "上場"
                ).\
                limit(per_page).offset((current_page-1) * per_page)
            # pagination用の検索結果総数を取得
            search_volume = db_session.query(Company).\
                filter(
                    Company.name.like('%' + company_name + '%'),\
                    Company.listing_category == "上場"
                ).count()
        else:
            companies = db_session.query(Company).\
            filter(Company.listing_category == "上場",Company.industry == industry).\
            limit(per_page).offset((current_page-1) * per_page)
            # pagination用の検索結果総数を取得
            search_volume = db_session.query(Company).\
                filter(Company.listing_category == "上場",Company.industry == industry).count()
    else:
        # リクエストフォームが存在しない場合はカテゴリ(産業)内の全ての企業を返す
        companies = db_session.query(Company).\
            filter(Company.listing_category == "上場",Company.industry == industry).\
            limit(per_page).offset((current_page-1) * per_page)
        # pagination用の検索結果総数を取得
        search_volume = db_session.query(Company).\
            filter(Company.listing_category == "上場",Company.industry == industry).count()

    page_disp_msg = '表示範囲 <b>{start}件 - {end}件 </b> 合計：<b>{total}</b>件'
    pagination = Pagination(page=current_page,
                            total=search_volume,
                            record_name='companiens',
                            per_page=per_page,
                            css_framework='bootstrap4',
                            link_size='25',
                            display_msg=page_disp_msg)

    db_session.close()
    return render_template('company/index.html',
                            companies=companies,
                            company_name=company_name,
                            industries=industries,
                            pagination=pagination)

@app.route('/company/<string:edinet_code>',methods=['GET'])
def show(edinet_code):
    '''
    会社表示
    '''
    db_session = DataBase.Session()
    company = db_session.query(Company).filter(Company.edinet_code == edinet_code).first()
    company_id = company.id
    # 役員と会社の中間テーブルと役員テーブルを取得 [OfficerCompany, Officer]
    officer_company_recs = db_session.query(OfficerCompany, Officer).\
        filter(OfficerCompany.company_id == company_id).\
        outerjoin(Officer, OfficerCompany.officer_id == Officer.id).\
        all()
    # おそらくコードはあってるがスクレイピングの不備で役員が表示されないことがある。
    officers = [rec[1] for rec in officer_company_recs]

    search_name = "%" + company.name.replace("株式会社","").strip() + "%"
    # 出身者を取得する
    # 経歴テーブルから特定の会社名で検索をかけ、
    # 現役役員は弾く
    # 社名を取得するためにCompanyをjoin
    former_officers = db_session.query(Career,Company).\
                    filter(
                        Career.description.like('%' + search_name + '%'),
                        not_(Career.edinet_code == edinet_code)
                    ).\
                    outerjoin(Company, Career.edinet_code == Company.edinet_code).\
                    all()
    # 役員の重複をpython側で弾く
    officer_name_list = []
    officer_list = []
    for officer in former_officers:
        if not(officer[0].name in officer_name_list):
            officer_name_list.append(officer[0].name)
            officer_list.append(officer)
    former_officers = officer_list
    db_session.close()
    return render_template('company/show.html',
                            company = company,
                            former_officers = former_officers,
                            officers = officers)
