# EDINET_DB (デモバージョン)
EDINETのAPIから得られる情報をもとに  
上場企業役員の経歴データを抽出しMySQLに保存。  
flaskで表示させるアプリケーション  
<br>
## 基本的なファイル構成
<br>

データベースの表示を担うwebアプリケーション部分(MCTモデル)と  
データベースのCRUD操作を行う部分に大別される。  
その他は全てデータ収集・クレンジングのためのライブラリ。  
ライブラリファイルは構造的に別のところにまとめるべきだがリファクタリングの手が回っていない。

- app
    - application.py
        - flaskのwebアプリケーション部分。主に表示専用
    - database.py
        - データベースのCRUD処理を記載する部分
    - models
    - controllers
    - templates
    - parse
        - スクレイピングの心臓部分。
    - api
    - manual_input
        - 最終的にエラーハンドリングしきれなかった有報を手動でデータ抽出するアプリ
<br>
<br>

# <font color=Dodgerblue>開発環境 外部モジュール</font>
#### 仮想環境(pipenv)を使うため、ローカルにはpipenvをインストールするだけで良い
<br>

- pipenv
- python 3.9.2
- MySQL 5.7
- mysqlclient
- SQLAlchemy
- Flask
- Fontawesome
<br>
<br>

## mysqlclient
MySQLをPythonで操作するためのドライバ
<br>
<br>

## SQLAlcamy
Python ORM(SQLを書かずにDBを操作するためのツール)
[使い方](https://it-engineer-lab.com/archives/1183)
<br>
<br>
<br>

# <font color=Dodgerblue>環境設定</font>
リポジトリをローカルの任意の場所にクローン後やること
## 設定ファイルの生成

```pipenv run init```

上記コマンドを実行すること以下のファイルを生成
- app/mysqlSecrets.yaml
- app/tmp
- app/tmp/ZIP
<br>
<br>

## mysqlSecrets.yamlにMysqlの認証情報を追加
user: ****  (クォーテーション不要)  
passwd: '********'
<br>
<br>

## pipfileを最新の状態にする
```pipenv update```
<br>
<br>

## モジュールのインストール

```pipenv install```
<br>
<br>
<br>


# <font color=Dodgerblue>pipenvの基本操作</font>

```pipenv shell``` 仮想環境に入る  
```exit``` 仮想環境をでる
<br>
<br>

## pipenvに新しいモジュールを追加

```pipenv install [モジュール名]```
<br>
<br>



## パッケージのバージョンアップ

```pipenv update```
<br>
<br>
<br>

# <font color=Dodgerblue>実行方法</font>
## データベースの実行ファイル
```python app/database.py```
<br>
<br>

## アプリケーションサーバの起動
```python app/application.py```
## servalで実行する場合
```
sudo $(which python) app/application.py
```
<br>
<br>

# <font color=Dodgerblue>プロジェクト構成について</font>
以下のページを参考にプロジェクト構成を行っている  
https://rinatz.github.io/python-book/ch04-06-project-structures/
<br>

## モデル構成について
モデルは以下の上下関係があり、下位のモデルは上位のモデルをソースに作られている。したがって上側のモデルファイルから下側のモデルを呼び出すことはない。（相互参照になり、エラーを吐く)

- DocumentIndex
- Company
    - Career
        - Officer
        - OfficerCompany
        - Company
<br>

## APIとモデルの関係
二種類のAPIとEDINETが公開する
- Meta API(有報のメタデータ) → DocumentIndex
- EDINET_CSV → Company
- Doc API(有報の本体データ) → Career
<br>
<br>

# <font color=Dodgerblue>コーディングスタイル</font>

## DB命名規則
- 複数単語はアンダーバーで区切る
- テーブル名、カラム名はスネークケース (みやすいから)
- 略名は利用しない
- modelsモジュール名もテーブル名に従う
<br>
<br>


##  クォーテーション
- 文字列にはシングルクォーテーションを用いる

- 基本的にpythonではシングルクォーテーションとダブルクォーテーションの文法的な違いはない。
- 以下の理由から基本的には文字列にはシングルクォーテーションを用いたい

<br>
<br>

##### 理由
- [一部の記事](http://trinitas.tech2019/04/03/python%E3%81%AB%E3%81%8A%E3%81%91%E3%82%8B%E3%82%B7%E3%83%B3%E3%82%B0%E3%83%AB%E3%82%AF%E3%82%A9%E3%83%BC%E3%83%86%E3%83%BC%E3%82%B7%E3%83%A7%E3%83%B3%E3%81%A8%E3%83%80%E3%83%96%E3%83%AB%E3%82%AF/)でダブルクォーテーションを使った文字列の
バグが発見されている(参照:2019-04-03)
- Slackにコードを貼った際にMacだとスマート引用符に変換される場合があり、バグの原因になる。[スマート引用符について](https://hatarakitakunai-hito.net/post-222/)
<br>
<br>

##  インデント


### インデントはスペース4つとする

- pythonの公式はインデントはスペース4つであると定めている
- VS_CODEはインデントの設定が楽だから問題ないと思う
<br>
<br>

## 二次元配列はフロントに渡さずにdictにする
例えば  
```records = [[companies],[officers]]```  
みたいな構造の二次元配列をフロントで取り出そうとすると
```
{% for rec in records %}
    <li>
        <p> {{ rec[0] }} </p>
        <p> {{ rec[1] }} </p>
    </li>
{% endfor %}
```
などという取り出し方になるが、これだとフロントだけを読んだときに何を取り出しているかわかりづらいので,  
```records = [{'company':[companies] 'officers':[officers]}]```  
のような形にすると
```
{% for rec in records %}
    <li>
        <p> {{ rec{'company'} }} </p>
        <p> {{ rec{'officers'} }} </p>
    </li>
{% endfor %}
```
何を取り出しているのかキーを見ればわかるのでより良い
# <font color=Dodgerblue>備忘録</font>
## VSCODEのimport error 対処法
- pipenvにimportしたmoduleがimport errorを吐く場合はVSCODEのinterpreterがpipenv環境のものに選択されているかを確認する。
- 自作moduleのimport errorはvscodeの環境設定を開き、extrapathsにそのmoduleのディレクトリパスを通す。  
<br>
<br>
## mecab-python3 の module import error対処法
Symbol not found: __ZN5MeCab11createModelEPKc
この記事読んでくれ↓
https://qiita.com/G1998G/items/2ad1b62c0285e478bfab
eg.)```/Users/jiro/Documents/edinet_db/app```
<br>
<br>
## ubuntu(研究室サーバー）でのmysqlclientのinstall error
```
sudo apt install libmysqlclient-dev
```
その後
```
pipenv install mysqlclient
```

# <font color=Dodgerblue>データソース</font>


- [EDINET操作概要](https://disclosure.edinet-fsa.go.jp/EKW0EZ0015.html)
- [EDINET_CODEのデータソース](https://disclosure.edinet-fsa.go.jp/E01EW/BLMainController.jsp?uji.bean=ee.bean.W1E62071.EEW1E62071Bean&uji.verb=W1E62071InitDisplay&TID=W1E62071&PID=W0EZ0001&SESSIONKEY=&lgKbn=2&dflg=0&iflg=0)（ページ下部）
- [法人番号公表サイト](https://www.houjin-bangou.nta.go.jp/download/zenken/)(使ってないけど参考までに)
