import pandas as pd
import requests
import json

def download_symbol_data(ticker,interval,start="0",end="9999999999"):
    '''
    Yahoo! Finance非公式APIから株価を取得する関数
    ticker : 証券コード4桁+.T 例)8035.T
    interval : [1m、5m、15m、30m、90m、1h、1d、5d、1wk、1mo、3mo]
    start : UNIXTIME 例）1468677212
    stop : UNIXTIME 例）1468677212
    '''
    headers = {
        'authority': 'query1.finance.yahoo.com',
        'cache-control': 'max-age=0',
        'sec-ch-ua': '^\\^',
        'sec-ch-ua-mobile': '?0',
        'dnt': '1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'sec-fetch-site': 'none',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-user': '?1',
        'sec-fetch-dest': 'document',
        'accept-language': 'ja,en-US;q=0.9,en;q=0.8',
        'cookie': 'APID=UP039bb088-ce15-11e8-84d2-02ac4f7bf59c; A3=d=AQABBDKwQl4CELkSvFZ7lIdHE9jF9y5cnVsFEgEBAQEBRF5MXgAAAAAA_eMAAAcIAKvAW3bKD4I&S=AQAAAhvz65O6LeGo-wQ_AFYmvBc; A1=d=AQABBDKwQl4CELkSvFZ7lIdHE9jF9y5cnVsFEgEBAQEBRF5MXgAAAAAA_eMAAAcIAKvAW3bKD4I&S=AQAAAhvz65O6LeGo-wQ_AFYmvBc; A1S=d=AQABBDKwQl4CELkSvFZ7lIdHE9jF9y5cnVsFEgEBAQEBRF5MXgAAAAAA_eMAAAcIAKvAW3bKD4I&S=AQAAAhvz65O6LeGo-wQ_AFYmvBc&j=WORLD; B=843uaepds1ao0&b=3&s=3l; GUC=AQEBAQFeRAFeTEIdRQRT; APIDTS=1626355968',
    }

    params = (
        ('symbol', str(ticker)),
        ('period1', str(start)),
        ('period2', str(end)),
        ('interval', str(interval)),
    )

    response = requests.get('https://query1.finance.yahoo.com/v8/finance/chart/' + str(ticker), headers=headers, params=params)
    resp_json = json.loads(response.text)

    data = resp_json['chart']['result'][0]

    return data


if __name__ == '__main__':
    # print(download_symbol_data("8035.T","1mo"))
    pass