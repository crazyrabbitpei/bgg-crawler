import urllib.request
from urllib.error import URLError, HTTPError
from bs4 import BeautifulSoup
import sys
import traceback
import ssl
import re
import json
import time

logger = None

try:
    from tool.MyLogger import MyLogger
    from tool.MyException.bgg import *
except ModuleNotFoundError:
    import logging
    # 如果不加這行則logger.setLevel就無法順利執行，因為在logging沒有呼叫basicConfig前都是沒有handler的，而預設writing to sys.stderr with a level of WARNING, and is used to handle logging events in the absence of any logging configuration
    # 隨便給予level，logger.setLevel在設定level
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('test')
    logger.setLevel(logging.DEBUG)
else:
    logger = MyLogger(log_path='./logs',log_file='{0}.log'.format(__name__), name=__name__)


DEFAULT_NO_VALUE = 'N/A'
main = 'https://boardgamegeek.com/browse/boardgame/page'
# get_bgid_title_and_year拿到tuple結果會拆成三個欄位儲存: 'bgid', 'title', 'year'
result_fields = ['rank', 'image', 'bgid', 'title',
                 'year', 'geekrating', 'avgrating', 'numvoters', 'others']
# 「未登入」時所顯示的欄位順序
fields = ['rank', 'image', 'bgid_title_and_year',
              'geekrating', 'avgrating', 'numvoters', 'others']


ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def get_rank(root, fieldname, field_index):
    if root.get('class')[0].strip() != "collection_rank":
        return -1
    if not root.find_all('a'):
        return DEFAULT_NO_VALUE

    return root.find_all('a')[0].get('name')


def get_image(root, fieldname, field_index):
    if root.get('class')[0].strip() != "collection_thumbnail":
        return -1
    if not root.find_all('a') or not root.find_all('a')[0].find_all('img'):
        return DEFAULT_NO_VALUE

    return root.find_all('a')[0].find_all('img')[0].get('src')


def get_bgid_title_and_year(root, fieldname, field_index):
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


def get_geekrating(root, fieldname, field_index):
    if root.get('class')[0].strip() != "collection_bggrating":
        return -1
    return root.string.strip()


def get_avgrating(root, fieldname, field_index):
    if root.get('class')[0].strip() != "collection_bggrating":
        return -1
    return root.string.strip()


def get_numvoters(root, fieldname, field_index):
    if root.get('class')[0].strip() != "collection_bggrating":
        return -1
    return root.string.strip()


def get_others(root, fieldname, field_index):
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

    field_index = 0
    for td in root.find_all('td'):
        value = field_extract[fields[field_index]](td, fields[field_index], field_index)

        if value == -1 or value == None: # -1代表欄位的DOM不符合預期
            raise RankListFieldFormatError("Page {page}, NO. {game_index}, Field {fname}({field_index}) 不符合預期格式".format(page=page,
                                                                                                           game_index=game_index, field_index=field_index+1, fname=fields[field_index]), traceback.format_exc())
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
        raise RankListFieldFormatError("Page {page}, NO. {game_index}({bgid}), Fields {fields} 值為 {default}".format(
            page=page, game_index=game_index, bgid=result['bgid'], fields=','.join(err_fields), default=DEFAULT_NO_VALUE), traceback.format_exc())

    return result

def has_nextpage(root, page):
    try:
        next_page = root.find('a', title='next page')
    except AttributeError:
        pass

    try:
        first_page = root.find('a', title='first page')
    except AttributeError:
        pass

    if not next_page and not first_page:
        raise RankListPageFormatError(
            '頁數的element格式不符合預期', traceback.format_exc())

    # 已是最後一頁
    if not next_page and first_page:
        return False

    logger.debug('Next page: {0}'.format(next_page.get('href')))
    return True

def default_store(result):
    #print(result)
    return


def get(mainurl, startpage=1, endpage=1, store=default_store, interval=10, cnt=0):
    """
    :param cnt: 紀錄已蒐集到的遊戲資訊數量
    """
    connect_error = False
    error_msg = None
    page = startpage
    while page <= endpage:
        url = "{mainurl}/{page}".format(mainurl=mainurl, page=page)
        logger.debug('{0}'.format(url))

        try:
            with urllib.request.urlopen(url, context=ctx) as fhand:
                data = fhand.read()
                soup = BeautifulSoup(data, 'html.parser')
        except HTTPError as e:
            error_msg = "{code}: {reason}({url})".format(
                code=e.code, reason=e.reason, url=url)
            connect_error = True
            break
        except URLError as e:
            error_msg = e.reason
            connect_error = True
            break
        except:
            error_msg = ','.join(sys.exc_info())
            connect_error = True
            break
        else:
            game_index = 0 # 遊戲在該頁的第幾位
            # 一欄遊戲資訊一個tr，最頂端為欄位文字
            for tr in soup.find_all('tr')[1:]:
                try:
                    result = parse_fields(tr, game_index, page)
                except RankListFieldFormatError as e:
                    raise
                else:
                    store(result, 'ranklist')
                    cnt += 1

                game_index += 1

            page += 1
            try:
                if has_nextpage(soup, page):
                    break
            except:
                raise


            time.sleep(interval)

    if connect_error:
        raise BggConnectionError(error_msg, traceback.format_exc())

    return (cnt, page-1)


# 指頂解析欄位函式
field_extract = {
    'rank': get_rank,
    'image': get_image,
    'bgid_title_and_year': get_bgid_title_and_year,
    'geekrating': get_geekrating,
    'avgrating': get_avgrating,
    'numvoters': get_numvoters,
    'others': get_others
}
if __name__ == '__main__':
    try:
        info = get(main, startpage=1, endpage=1)
    except RankListFieldFormatError as e:
        logger.error(e.args)
    except:
        logger.error(traceback.format_exc())
    else:
        logger.info('Total game: {0}, Last page: {1}'.format(*info))
