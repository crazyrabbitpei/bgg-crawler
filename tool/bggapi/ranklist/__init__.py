import urllib.request
from urllib.error import URLError, HTTPError
from bs4 import BeautifulSoup
import sys
import ssl
import re
import json
import time

main = 'https://boardgamegeek.com/browse/boardgame/page/'

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def get_rank(root):
    if root.get('class')[0].strip() != "collection_rank":
        return -1
    return root.find_all('a')[0].get('name')

def get_image(root):
    if root.get('class')[0].strip() != "collection_thumbnail":
        return -1
    return root.find_all('a')[0].find_all('img')[0].get('src')
def get_bgid_title_and_year(root):
    if root.get('class')[0].strip() != "collection_objectname":
        return -1
    info = root.find('div', id=re.compile("^results_objectname"))
    link_and_title = info.find_all('a')[0]
    link = link_and_title.get('href')
    bgid = re.search(r'/boardgame/(.*)/', link).group(1)
    title = link_and_title.string.strip()
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
            raise SyntaxError("Page {page}, NO. {rank} , Field {field_index} 不符合預期格式: {fname}".format(page=page,
                rank=game_index, field_index=field_index+1, fname=field_extract[field_index]))
        else:
            if type(value) == tuple:
                result_values.extend(value)
            else:
                result_values.append(value)
        field_index += 1
    result = dict(zip(result_fields, result_values))
    del_nonused_fields(result)
    return result

def has_nextpage(root):
    try:
        next_page = root.find('a', title='next page').get('href')
    except AttributeError:
        return False
    else:
        #print(next_page)
        return True

def default_store(result, cnt):
    print(result)
    return


def get(main, page=1, limit=-1, store=default_store, interval=10, cnt=0):
    url = "{main}/{page}".format(main=main, page=page)
    try:
        with urllib.request.urlopen(url, context=ctx) as fhand:
            data = fhand.read()
            soup = BeautifulSoup(data, 'html.parser')
    except HTTPError as e:
        print("{code}: {reason}({url})".format(code=e.code, reason=e.reason, url=url))
        return (cnt, page-1)
    except URLError as e:
        print(e.reason)
        return (cnt, page-1)
    except:
        print(sys.exc_info())
        return (cnt, page-1)
    else:
        game_index = 0 # 遊戲在該頁的第幾位
        # 最頂端為欄位文字
        for tr in soup.find_all('tr')[1:]:
            store(parse_fields(tr, game_index, page), cnt)
            cnt += 1
            game_index += 1

        page += 1
        if limit != -1 and page > limit:
            return (cnt, page-1)

        if has_nextpage(soup):
            time.sleep(interval)
            return get(main, page, limit, store, interval, cnt)
        else:
            return (cnt, page)

if __name__ == '__main__':
    info = get(main, page=1, limit=1)
    print('Total game: {0}, Last page: {1}'.format(*info))
