import urllib.request
from urllib.error import URLError, HTTPError
from bs4 import BeautifulSoup
import sys
import ssl
import re
import json
import time
import logging
from logging.handlers import TimedRotatingFileHandler


DEFAULT_NO_VALUE = 'N/A'
main = 'https://boardgamegeek.com/browse/boardgame/page/'

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def get_rank(root):
    if root.get('class')[0].strip() != "collection_rank":
        return -1
    if not root.find_all('a'):
        return DEFAULT_NO_VALUE

    return root.find_all('a')[0].get('name')

def get_image(root):
    if root.get('class')[0].strip() != "collection_thumbnail":
        return -1
    if not root.find_all('a') or not root.find_all('a')[0].find_all('img'):
        return DEFAULT_NO_VALUE

    return root.find_all('a')[0].find_all('img')[0].get('src')

def get_bgid_title_and_year(root):
    bgid = DEFAULT_NO_VALUE
    title = DEFAULT_NO_VALUE
    year = DEFAULT_NO_VALUE

    if root.get('class')[0].strip() != "collection_objectname":
        return -1
    info = root.find('div', id=re.compile("^results_objectname"))
    if not info.find_all('a'):
        return (bgid, title, year)

    link_and_title = info.find_all('a')[0]
    link = link_and_title.get('href')

    groups = re.search(r'/boardgame[\w]*/([\d]+)/', link)
    if groups:
        bgid = groups.group(1)

    title = link_and_title.string.strip()

    if info.find_all('span'):
        year = info.find_all('span')[0].string
        p = re.compile('[()]')
        year = p.sub('', year).strip()

    return (bgid, title, year)
def get_geekrating(root):
    if root.get('class')[0].strip() != "collection_bggrating":
        return -1
    return root.string.strip()
def get_avgrating(root):
    if root.get('class')[0].strip() != "collection_bggrating":
        return -1
    return root.string.strip()
def get_numvoters(root):
    if root.get('class')[0].strip() != "collection_bggrating":
        return -1
    return root.string.strip()
def get_others(root):
    return root.get_text


def del_nonused_fields(data):
    del data['image']
    del data['others']


def detect_fields(data):
    flag = True
    err_fields = []
    check_fields = ['bgid', 'title']
    for field in check_fields:
        if data[field] == DEFAULT_NO_VALUE:
            flag = False
            err_fields.append(field)

    return (flag, err_fields)

def parse_fields(root, game_index, page):
    result_values = []
    # get_bgid_title_and_year拿到tuple結果會拆成三個欄位儲存: 'bgid', 'title', 'year'
    result_fields = ['rank', 'image', 'bgid', 'title',
                     'year', 'geekrating', 'avgrating', 'numvoters', 'others']

    # 按欄位順序解析: 以下順序為「未登入」時所顯示的欄位
    field_index = 0
    fields = ['rank', 'image', 'bgid_title_and_year',
              'geekrating', 'avgrating', 'numvoters', 'others']
    field_extract = {
        'rank': get_rank,
        'image': get_image,
        'bgid_title_and_year': get_bgid_title_and_year,
        'geekrating': get_geekrating,
        'avgrating': get_avgrating,
        'numvoters': get_numvoters,
        'others': get_others
    }
    for td in root.find_all('td'):
        value = field_extract[fields[field_index]](td)

        if value == -1 or value == None: # -1代表欄位的DOM不符合預期
            raise SyntaxError("Page {page}, NO. {game_index}, Field {fname}({field_index}) 不符合預期格式".format(page=page,
                                                                                                           game_index=game_index, field_index=field_index+1, fname=fields[field_index]))
        else:
            if type(value) == tuple:
                result_values.extend(value)
            else:
                result_values.append(value)
        field_index += 1
    result = dict(zip(result_fields, result_values))
    del_nonused_fields(result)

    ok, err_fields = detect_fields(result)
    if not ok:
        raise SyntaxError("Page {page}, NO. {game_index}({bgid}), Fields {fields} 值為 {default}".format(page=page, game_index=game_index, bgid=result['bgid'], fields=','.join(err_fields), default=DEFAULT_NO_VALUE))

    return result

def has_nextpage(root, page):
    try:
        next_page = root.find('a', title='next page').get('href')
    except AttributeError:
        logging.error('第 {0} 頁的next page link 格式不符合預期'.format(page))
        return False
    else:
        #logging.debug(next_page)
        return True

def default_store(result, cnt):
    print(result)
    return


def get(main, startpage=1, endpage=float('Inf'), store=default_store, interval=10, cnt=0):
    """
    :param cnt: 紀錄已蒐集到的遊戲資訊數量
    """
    page = startpage
    while page <= endpage:
        url = "{main}/{page}".format(main=main, page=page)
        logging.info('{0}'.format(url))

        try:
            with urllib.request.urlopen(url, context=ctx) as fhand:
                data = fhand.read()
                soup = BeautifulSoup(data, 'html.parser')
        except HTTPError as e:
            logging.error("{code}: {reason}({url})".format(
                code=e.code, reason=e.reason, url=url))
            break
        except URLError as e:
            logging.error(e.reason)
            break
        except:
            logging.error(sys.exc_info())
            break
        else:
            game_index = 0 # 遊戲在該頁的第幾位
            # 一欄遊戲資訊一個tr，最頂端為欄位文字
            for tr in soup.find_all('tr')[1:]:
                try:
                    result = parse_fields(tr, game_index, page)
                except SyntaxError as e:
                    logging.error(e.msg)
                else:
                    store(result, cnt)
                    cnt += 1

                game_index += 1

            if not has_nextpage(soup, page):
                break

            page += 1
            time.sleep(interval)

    return (cnt, page-1)

if __name__ == '__main__':
    info = get(main, startpage=1193, endpage=1194)
    print('Total game: {0}, Last page: {1}'.format(*info))
