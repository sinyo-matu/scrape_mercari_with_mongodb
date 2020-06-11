import requests
import lxml.html
from pymongo import MongoClient
import re
import time
import datetime

def main():
          client = MongoClient('#mongodb server')
          db = client.mercari
          collection = db.some_search_result
          collection.create_index('key', unique=True)
          session = requests.Session()

          url = 'target url(mercaris search result page)'
          headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36'}

          response = session.get(url, headers=headers)
          urls = scrape_list_page(response) #一覧ページをスクレプします。urlリストのGeneratorを得る。
          for url in urls:
                    key = extract_key(url[0])
                    item = collection.find_one({'key':key}) #商品番号keyでdbを検索する。
                    if not item :
                              time.sleep(1)
                              response = session.get(url[0], headers=headers)
                              item = scrape_detail_page(response)
                              collection.insert_one(item) #商品が存在しなければ追加する。
                    else:
                              if url[1] == 0: #urlリストが持つ商品の在庫情報をチェックする。
                                        if item['item_exist'] == 1:
                                                  sold_time = datetime.datetime.now()
                                                  collection.update_one({'key':key}, {"$set":{"item_exist":0}}) #商品が存在なければ、ステータス更新する。
                                                  collection.update_one({'key':key}, {'$set':{"sold_time":sold_time}}) 
                                                  print("商品がsold outした", item['item_name'], item['url'])                   

def scrape_list_page(response):          #一覧ページのスクレピング関数
          root = lxml.html.fromstring(response.content)
          root.make_links_absolute(response.url)
          for items in root.cssselect('section.items-box'):
                    a=items.cssselect('a')
                    s=items.cssselect('div.item-sold-out-badge') #一覧ページの商品の在庫ステータスをチェックする。
                    if not s:
                              x = 1 #在庫していれば1
                    else:
                              x = 0 #在庫してなければ0 一覧ページでチェックすることによって詳細ページのチェックを省ける

                    yield [a[0].get('href'), x] #urlと在庫ステータスのリストを返す。　

def scrape_detail_page(response):
          root = lxml.html.fromstring(response.content)
          item_name_element = root.cssselect('h1.item-name')
          item_name = item_name_element[0].text
          item_price_element = root.cssselect('span.item-price')
          item_price = item_price_element[0].text
          item_shipping_fee_element = root.cssselect('span.item-shipping-fee')
          item_shipping_fee = item_shipping_fee_element[0].text
          item_description_element = root.cssselect('p.item-description-inner')
          item_description = item_description_element[0].text
          key = extract_key(response.url)
          item_photo_element = root.cssselect('div.owl-item-inner')
          item_photo_url_element = item_photo_element[0].cssselect('img')
          item_photo_url = item_photo_url_element[0].get('data-src')
          item_sold_out_badge_element = root.cssselect('div.item-sold-out-badge')
          if not item_sold_out_badge_element:
                    exist = 1
                    sold_time = datetime.datetime(1,1,1,1,1,1,1)
          else:
                    exist =0
                    sold_time = datetime.datetime.now()
          
          item = {
                    'datetime':datetime.datetime.now(),
                    'key':key,
                    'url':response.url,
                    'item_name':item_name,
                    'item_price':item_price,
                    'item_shipping_fee':item_shipping_fee,
                    'item_photo_url':item_photo_url,
                    'item_description':item_description,
                    'item_exist':exist,
                    'sold_time':sold_time,
          }
          return item

def extract_key(url):
          m = re.search(r'.*items/(m[0-9]*?)/', url) #urlから商品番号を取得する。
          return m.group(1)

if __name__ == '__main__':
          main()