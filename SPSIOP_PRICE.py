# -*-coding=utf-8-*-

# @Time : 2019/10/20 23:14
# @File : SPSIOP_PRICE.py
# 获取SPSIOP的价格，每天早上美股收盘
# 先获取xop的前一天的涨幅，然后在前一天华宝油气的基础上相加

import datetime
import requests
import pymongo
from settings import llogger, _json_data, send_from_aliyun,notify

BASE_INFO = _json_data['mongo']['qq']
host = BASE_INFO['host']
port = BASE_INFO['port']
user = BASE_INFO['user']
password = BASE_INFO['password']

to_mail = _json_data['mail']['qq']['user']

connect_uri = f'mongodb://{user}:{password}@{host}:{port}'
client = pymongo.MongoClient(connect_uri)
doc = client['db_stock']['SPSIOP']

# 先访问一下雪球首页得到cookies

logger = llogger('log/huabaoyouqi.log')

home_headers = {'User-Agent': 'Xueqiu App'}

headers = {'User-Agent': 'Xueqiu App',
           'Access-Control-Allow-Origin': 'https://xueqiu.com',
           'Content-Type': 'application/json;charset=UTF-8',
           'P3P': 'CP="IDC DSP COR ADM DEVi TAIi PSA PSD IVAi IVDi CONi HIS OUR IND CNT"'}

xueqiu_url = 'https://stock.xueqiu.com/v5/stock/quote.json?symbol=.SPSIOP&extend=detail'
home_page = 'https://xueqiu.com'
today = datetime.datetime.now().strftime('%Y-%m-%d')


def predict_price():
    session = requests.Session()
    session.get(url=home_page, headers=home_headers)

    r = session.get(url=xueqiu_url,
                    headers=headers)

    js_data = r.json()

    quote = js_data.get('data', {}).get('quote')

    quote['crawltime'] = datetime.datetime.now()
    doc.insert_one(quote)
    percent = quote.get('percent')
    jsl_qdii,est_val_dt = qdii_info()

    if jsl_qdii:
        predict_v = round((1 + percent * 0.95 * 0.01) * jsl_qdii, 3)
        logger.info(f'最新估值{predict_v}')
        d = {'日期': today, '估值': predict_v}
        client['db_stock']['huabaoyouqi_predict'].insert_one(d)
        title = f'华宝估值{predict_v} 净值日期{est_val_dt[5:]}'
        send_from_aliyun(title, '')

    else:
        notify('华宝油气获取估值失败')


def qdii_info():
    url = 'https://www.jisilu.cn/data/qdii/qdii_list/?rp=25&page=1'
    r = requests.get(url=url, headers=home_headers)
    js_data = r.json()
    rows = js_data.get('rows', [])
    new_rows = []
    for row in rows:
        new_rows.append(row.get('cell'))
    doc_ = client['DB_QDII'][today]

    try:
        doc_.insert_many(new_rows)

    except Exception as e:
        logger.error(e)

    next_url = 'https://www.jisilu.cn/data/qdii/qdii_list/C?___jsl=LST___t=1604513012662&rp=22'
    r = requests.get(url=next_url, headers=home_headers)
    js_data = r.json()
    rows = js_data.get('rows', [])

    for row in rows:
        if row.get('cell', {}).get('fund_nm') == '华宝油气':

            nav = row.get('cell', {}).get('fund_nav')
            est_val_dt = row.get('cell', {}).get('est_val_dt')

            try:
                nav = float(nav)  # 网站给的是字符
            except:
                return None
            else:
                return nav,est_val_dt


if __name__ == '__main__':
    predict_price()
