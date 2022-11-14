from selenium import webdriver
from selenium.webdriver.common.by import By
import re
from bs4 import BeautifulSoup
import requests
import pandas as pd
from time import sleep

PAGE_BASE_URL = 'https://www.traders.co.jp'
PAGE_RESULT_NUM = 100

chrome = webdriver.Chrome()
chrome.get(PAGE_BASE_URL + '/market_jp/screening')


# 検索画面
close_price_checkbox = chrome.find_element(By.XPATH, '//*[@id="flg_sel03"]')
close_price_max_input = chrome.find_element(
    By.XPATH, '//*[@id="close_price_max"]')
search_submit_button = chrome.find_element(By.XPATH, '//*[@id="submit_btn"]')

close_price_checkbox.click()
close_price_max_input.send_keys('200')
search_submit_button.click()

# 検索結果
search_result_num_text_elm = chrome.find_element(
    By.XPATH, '//*[@id="content_area"]/div[2]/div/div[1]/div[1]/div[2]/div[1]')
search_result_num_text = search_result_num_text_elm.get_attribute('innerHTML')
search_result_num = int(re.sub(r"\D", "", search_result_num_text))
page_total_num = (search_result_num // PAGE_RESULT_NUM)\
    if search_result_num % PAGE_RESULT_NUM == 0\
    else (search_result_num // PAGE_RESULT_NUM) + 1

# 検索結果の企業のリンク一覧を生成


def search_result_page_parser():
    stock_result_url_list = []
    stock_table_body = chrome.find_element(
        By.XPATH, '//*[@id="content_area"]/div[2]/div/div[1]/div[1]/div[5]/div[1]/div[2]/table/tbody')
    stock_rows = stock_table_body.find_elements(By.TAG_NAME, 'tr')
    for stock_row in stock_rows:
        try:
            stock_row_data_list = stock_row.find_elements(By.TAG_NAME, 'td')
            stock_url = stock_row_data_list[1].find_element(
                By.TAG_NAME, 'a').get_attribute('href')
            # print(stock_url)
            stock_result_url_list.append(stock_url)
        except:
            # 行の途中にあるヘッダを避ける
            pass
    return stock_result_url_list


stock_url_list = []
for page_num in range(1, page_total_num+1):
    #print('page:', page_num)
    stock_url_list.extend(search_result_page_parser())
    if (page_num < page_total_num):
        next_page_button = chrome.find_element(
            By.XPATH,
            '//*[@id="content_area"]/div[2]/div/div[1]/div[1]/div[5]/div[2]/nav/ul/li[@class="page-item active"]/following::li')
        next_page_button.click()


def get_stock_info(stock_page_url: str):
    # 株メインページ
    stock_page = requests.get(stock_page_url)
    stock_page_bs = BeautifulSoup(stock_page.text, 'html.parser')

    # 株情報
    stock_basic_data = stock_page_bs.find(
        name='div', class_='basic_data p-2 p-md-3')
    stock_name = stock_basic_data.find(
        name='h1', class_='name mb-md-2 mb-1').text
    stock_id = int(re.sub(r"\D", "", stock_basic_data.find(name='div').text))
    #print('銘柄名:', stock_name)
    #print('銘柄番号:', stock_id)

    print(stock_id, stock_name, stock_page_url, 'を解析しています...')

    # 株価データ
    stock_price_table = stock_page_bs.find(
        name='table', class_='data_table price')
    stock_price_rows = stock_price_table.find_all(name='tr')
    stock_close_price = int(stock_price_rows[3].find(name='td').text)
    #print('前日終値:', stock_close_price)

    # 投資データ
    stock_fundamental_table = stock_page_bs.find(
        name='table', class_='data_table fundamental')
    stock_fundamental_rows = stock_fundamental_table.find_all(name='tr')
    stock_PER_text = stock_fundamental_rows[0].find(
        name='td').text.replace('倍', '')
    stock_PER = float(stock_PER_text) if stock_PER_text != '-' else None
    stock_PBR_text = stock_fundamental_rows[1].find(
        name='td').text.replace('倍', '')
    stock_PBR = float(stock_PBR_text) if stock_PBR_text != '-' else None
    stock_market_value = stock_fundamental_rows[7].find(name='td').text
    stock_market_value = int(
        re.sub(r"\D", "", stock_fundamental_rows[7].find(name='td').text)) * 1000000
    stock_issued_stock_num = int(
        re.sub(r"\D", "", stock_fundamental_rows[8].find(name='td').text)) * 1000000
    #print('PER:', stock_PER, '倍')
    #print('PBR:', stock_PBR, '倍')
    #print('時価総額:', stock_market_value, '円')
    #print('発行済株数:', stock_issued_stock_num, '株')

    # 信用取引データ
    # stock_margin_trade_mb3_table = stock_page_bs.find(
    # name='table', class_='data_table margin_trade mb-3')
    # stock_margin_trade_table = stock_page_bs.find(
    # name='table', class_='data_table margin_trade')

    # 株財務ページ
    stock_page_finance_url = stock_page_url + '/fundamental'
    stock_page_finance = requests.get(stock_page_finance_url)
    stock_page_finance_bs = BeautifulSoup(
        stock_page_finance.text, 'html.parser')

    # 財務データ
    stock_finance_table = stock_page_finance_bs.find(
        name='table', class_='data_table inner_elm fin_table')
    try:
        stock_finance_rows = stock_finance_table.find_all(name='tr')
        stock_latest_equity_ratio = float(stock_finance_rows[3].find_all(name='td')[
            0].text)/100
    except:
        stock_latest_equity_ratio = None
    #print('自己資本比率:', stock_latest_equity_ratio, ' %')

    # テクニカルページ
    stock_page_technical_url = stock_page_url + '/technical'
    stock_page_technical = requests.get(stock_page_technical_url)
    stock_page_technical_bs = BeautifulSoup(
        stock_page_technical.text, 'html.parser')

    # 移動平均乖離率データ
    stock_technical_tables = stock_page_technical_bs.find_all(
        name='table', class_='data_table tech')
    stock_technical_ma_table = stock_technical_tables[2]
    stock_technical_ma_rows = stock_technical_ma_table.find_all(name='tr')
    stock_ma_200days_price_text = stock_technical_ma_rows[3].find_all(name='td')[
        0].text
    stock_ma_200days_price = int(stock_ma_200days_price_text)\
        if stock_ma_200days_price_text != '-' else None
    stock_ma_13week_price_text = stock_technical_ma_rows[4].find_all(name='td')[
        0].text
    stock_ma_13week_price = int(stock_ma_13week_price_text)\
        if stock_ma_13week_price_text != '-' else None
    #print('200日移動平均:', stock_ma_200days_price)
    #print('13週移動平均:', stock_ma_13week_price)

    stock_info_dict = {
        'traders.co.jp_url': stock_page_url,
        '銘柄名': stock_name,
        '銘柄ID': stock_id,
        '前日終値': stock_close_price,
        'PER': stock_PER,
        'PBR': stock_PBR,
        '時価総額': stock_market_value,
        '発行済株数': stock_issued_stock_num,
        '自己資本比率': stock_latest_equity_ratio,
        '200日移動平均': stock_ma_200days_price,
        '200日移動平均乖離率': (stock_ma_200days_price / stock_close_price)-1 if stock_ma_200days_price else None,
        '13週移動平均': stock_ma_13week_price,
        '13週移動平均乖離率': (stock_ma_13week_price / stock_close_price)-1 if stock_ma_13week_price else None
    }
    sleep(1)

    return stock_info_dict


stock_info_dict = [get_stock_info(stock_page_url)
                   for stock_page_url in stock_url_list]
stock_info_df = pd.DataFrame(stock_info_dict)

stock_info_df.to_csv('低位株.csv')
