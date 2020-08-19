import pandas as pd
import urllib.request
from urllib.error import URLError, HTTPError
from bs4 import BeautifulSoup
import sys, traceback
import ssl
import re
import json
import time
import bs4

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
    logger = MyLogger(log_path='./logs',
                      log_file='{0}.log'.format(__name__), name=__name__)

# 桌遊資訊會被包在script的這個參數裡
DEFAULT_PRELOAD_INFO = 'GEEK.geekitemPreload'
DEFAULT_NO_VALUE = 'N/A'
main = 'https://boardgamegeek.com/boardgame' # 這種方式需要自行parse出script裡的資訊
# 另一種api: https://api.geekdo.com/api/geekitems?nosession=1&objecttype=thing&subtype=boardgame，可直接得到json


# 2020/08/16網頁版結果
# 網頁版的欄位
fields = ['itemdata', 'relatedlinktypes', 'linkedforum_types', 'subtypename', 'rankinfo', 'polls', 'stats', 'relatedcounts', 'itemid', 'objecttype', 'objectid', 'label', 'labelpl', 'type', 'id', 'href', 'subtype', 'subtypes', 'versioninfo', 'name', 'alternatename', 'yearpublished', 'minplayers', 'maxplayers', 'minplaytime', 'maxplaytime', 'minage', 'override_rankable', 'targetco_url', 'walmart_id', 'instructional_videoid', 'summary_videoid', 'playthrough_videoid', 'focus_videoid', 'bggstore_product', 'short_description', 'links', 'linkcounts', 'secondarynamescount', 'alternatenamescount', 'primaryname', 'description', 'wiki', 'website', 'imageid', 'images', 'imagepagehref', 'imageurl', 'topimageurl', 'itemstate', 'promoted_ad', 'special_user']
# bgg api版欄位
api_fields = ['itemid', 'objecttype', 'objectid', 'label', 'labelpl', 'type', 'id', 'href', 'subtype', 'subtypes', 'versioninfo', 'name', 'alternatename', 'yearpublished', 'minplayers', 'maxplayers', 'minplaytime', 'maxplaytime', 'minage', 'override_rankable', 'targetco_url', 'walmart_id', 'instructional_videoid', 'summary_videoid', 'playthrough_videoid', 'focus_videoid', 'bggstore_product', 'short_description', 'links', 'linkcounts', 'secondarynamescount', 'alternatenamescount', 'primaryname', 'alternatenames', 'description', 'wiki', 'website', 'imageid', 'images', 'imagepagehref', 'imageurl', 'topimageurl', 'itemstate', 'promoted_ad', 'special_user']
# 語言需求等級
languagedependences = {
    'No necessary in-game text': 1,
    'Some necessary text - easily memorized or small crib sheet': 2,
    'Moderate in-game text - needs crib sheet or paste ups': 3,
    'Extensive use of text - massive conversion needed to be playable': 4,
    'Unplayable in another language	': 5
}
"""
期望儲存欄位
"""
# 網頁版的欄位
require_fields = ['rankinfo', 'polls', 'stats',
                 'relatedcounts', 'id', 'href', 'name', 'yearpublished', 'minplayers', 'maxplayers', 'minplaytime', 'maxplaytime', 'minage', 'short_description', 'linkcounts', 'alternatenamescount', 'description', 'images', 'imageurl', 'topimageurl']
# bgg api版欄位: links和
api_require_fields = ['links', 'alternatenames']

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def _check_field(main, field, item):
    # if type(field) == list and len(items) > 0:
    #     for m in field:
    #         if m not in items[0]:
    #             raise BgInfoNotComplete('{0} 沒有 {1} 欄位: {2}'.format(main,
    #                 field, items[0]), traceback.format_exc())
    if field not in item:
        raise BgInfoNotComplete('{0} 沒有 {1} 欄位: {2}'.format(main,
            field, item), traceback.format_exc())


def get_alternatenames(items):
    """alternatenames: [{nameid, name}]
        - nameid: str
        - name: str，不同國家有不同遊戲名稱
    """
    try:
        _check_field('alternatenames', 'alternatenames', items)
    except:
        raise

    return items['alternatenames']

def get_rank_info(items):
    """rankinfo: [{veryshortprettyname, rank, baverage}]
        - veryshortprettyname: Overall/Strategy...，排名種類
        - rank: str，在該種類的名次
        - beverage: str，geek rating
    """
    try:
        _check_field('rankinfo', 'rankinfo', items)
    except:
        raise

    result = dict()
    # 遊戲排名除了overall之外還有family, strategy...，這項資訊要額外存放: {type, rank}
    other_category_rank_results = []

    for item in items['rankinfo']:
        main_name = '{veryshortprettyname}'.format(**item).lower().strip()
        #print(main_name)
        if main_name == 'overall':
            field_name = '{0}_rank'.format(main_name)
            result[field_name] = item['rank']
            field_name = '{0}_baverage'.format(main_name)
            result[field_name] = item['baverage']
        else:
            other_category_rank_results.append(
                {'type': main_name, 'rank': item['rank']})

    #print(other_category_rank_results)
    return (result, other_category_rank_results)


def get_polls(items):
    """polls: {userplayers, playerage, languagedependence, boardgameweight}
        - userplayers: {best, recommended, totalvotes}，min/max可能為null或int
            - best: [{min, max}]，最佳遊戲人數
            - recommended: [{min, max}]，最佳遊戲人數
            - totalvotes: str，同票人數
        - playerage: str，適合年零
        - languagedependence: str，文字需求說明
        - boardgameweight: {averageweight, votes}
            - averageweight: float，ex: 3.265625，遊戲重度(1~5)
            - votes: str，同票人數
    """
    try:
        _check_field('polls', 'polls', items)
    except:
        raise

    result = dict()
    polls = items['polls']

    userplayers = polls['userplayers']
    for field in userplayers.keys():
        player_min = 0
        player_max = 0
        if field == 'totalvotes':
            result[field] = userplayers[field]
            continue

        for info in userplayers[field]:
            player_min = info['min']
            player_max = info['max']


            result['polls_userplayers_{0}_min'.format(
                field)] = player_min
            result['polls_userplayers_{0}_max'.format(
                field)] = player_max

            if player_min and player_max:
                break

        if not player_min:
            raise BgInfoNotComplete(
                '無法得到正確的polls_userplayers_{0}_min'.format(field), traceback.format_exc())
        if not player_max:
            raise BgInfoNotComplete(
                '無法得到正確的polls_userplayers_{0}_max'.format(field), traceback.format_exc())

    boardgameweight = polls['boardgameweight']
    for field in boardgameweight.keys():
        result['polls_boardgameweight_{0}'.format(
            field)] = boardgameweight[field]

    result['playerage'] = polls['playerage']
    result['languagedependence'] = languagedependences.get(polls['languagedependence'], -1)
    if result['languagedependence'] == -1:
        raise BgInfoLanguageDependenceUndefined(
            '尚未定義的語言依賴類別: {0}'.format(polls['languagedependence']), traceback.format_exc())
    return result


def _get_links(main, items):
    result = []
    require_fields = ['name', 'objecttype', 'objectid']
    for field in require_fields:
        for item in items:
            try:
                _check_field(main, field, item)
            except:
                raise

    name_need_cut = False
    # name欄位需要做裁切
    if main in ['boardgamefamily']:
        name_need_cut = True

    for item in items:
        tmp = dict()
        for field in require_fields:
            value = item.get(field, DEFAULT_NO_VALUE)
            if field == 'name' and name_need_cut:
                family, famliy_value  = value.split(':')
                tmp['family'] = family.strip()
                tmp['famliy_value'] = famliy_value.strip()
            tmp[field] = value
        result.append(tmp)
    return result


def _trans_to_csv_writable_format(data, require_fields):
    values = []
    for info in data:
        columns, value = list(zip(*info.items()))
        values.append(value)

    return dict(list(zip(columns, list(zip(*values)))))

def get_links(items):
    """links: {'boardgamedesigner', 'boardgameartist', 'boardgamepublisher', 'boardgamehonor', 'boardgamecategory', 'boardgamemechanic', 'boardgameexpansion', 'boardgameversion', 'boardgamefamily'}
        - boardgamedesigner/boardgameartist/boardgamepublisher/boardgamehonor/boardgamecategory/boardgamemechanic/boardgameexpansion/boardgameversion/boardgamefamily: [{name, objecttype, objectid}]。boardgamehonor為獲得獎項，boardgamefamily為遊戲背景(種類會放在name裡， ex: Theme: Samurai、Country: Japan、Components: Miniatures)
            - name: str
            - objecttype: str，person/company/family/property/thing/version...
                - person: boardgamedesigner/boardgameartist
                - company: boardgamepublisher
                - family: boardgamehonor/boardgamefamily
                - property: boardgamecategory/boardgamemechanic
                - thing: boardgameexpansion
                - version: boardgameversion
            - objectid: str
        - web結果每個項目最多顯示6筆，所以boardgamepublisher/boardgamehonor/boardgameexpansion/boardgameversion無法透過此web蒐集完整，野生api則可以蒐集完整

    結果直接回傳csv格式
    """
    try:
        _check_field('links', 'links', items)
    except:
        raise

    #format_result = dict()
    result = dict()
    require_fields = ['boardgamedesigner', 'boardgameartist', 'boardgamepublisher', 'boardgamehonor', 'boardgamecategory', 'boardgamemechanic', 'boardgameexpansion', 'boardgameversion', 'boardgamefamily']
    links = items['links']

    for field in require_fields:
        try:
            _check_field(field, field, links)
        except:
            raise

        result[field] = _get_links(field, links[field])
        # result = _get_links(field, links[field])
        # if len(result) > 0:
        #     format_result[field] = _trans_to_csv_writable_format(result, require_fields)

    return (result, require_fields)

def get_stats(items):
    """stats: {'usersrated', 'average', 'baverage', 'stddev', 'avgweight', 'numweights', 'numgeeklists', 'numtrading', 'numwanting', 'numwish', 'numowned', 'numprevowned', 'numcomments', 'numwishlistcomments', 'numhasparts', 'numwantparts', 'views', 'playmonth', 'numplays', 'numplays_month', 'numfans'}，numfans為int，其餘都為str
        - average: 玩家總平均
        - baverage: geek總平均
    """
    try:
        _check_field('stats', 'stats', items)
    except:
        raise

    stats = items['stats']
    result = dict()
    for field in stats.keys():
        main = 'stats_{0}'.format(field)
        result[main] = stats[field]
    return result


def get_relatedcounts(items):
    """relatedcounts: {'news', 'blogs', 'weblink', 'podcast'}，都為int
    """
    try:
        _check_field('relatedcounts', 'relatedcounts', items)
    except:
        raise

    relatedcounts = items['relatedcounts']
    result = dict()
    for field in relatedcounts.keys():
        main = 'relatedcounts_{0}'.format(field)
        result[main] = relatedcounts[field]
    return result

def get_linkcounts(items):
    """linkcounts: {'boardgamedesigner', 'boardgameartist', 'boardgamepublisher', 'boardgamehonor', 'boardgamecategory', 'boardgamemechanic', 'boardgameexpansion', 'boardgameversion', 'expandsboardgame', 'boardgameintegration', 'contains', 'containedin', 'reimplementation', 'reimplements', 'boardgamefamily', 'videogamebg', 'boardgamesubdomain', 'boardgameaccessory', 'commerceweblink'}，都是int
    """
    try:
        _check_field('linkcounts', 'linkcounts', items)
    except:
        raise

    linkcounts = items['linkcounts']
    result = dict()
    for field in linkcounts.keys():
        main = 'linkcounts_{0}'.format(field)
        result[main] = linkcounts[field]
    return result


def get_images(items):
    """images: {thumb, square200, previewthumb}，由小到大張遊戲圖片link，ex: https://cf.geekdo-images.com/thumb/img/SJV333FxGVxsOc2XYvtVYx-uMDU=/fit-in/200x150/pic3880340.jpg
    imageurl: str，遊戲圖片，ex: https://cf.geekdo-images.com/itemrep/img/7KmSH1xYiDDOcIQptnQoXSeOfLU=/fit-in/246x300/pic3880340.jpg
    """
    try:
        _check_field('images', 'images', items)
    except:
        raise

    images = items['images']
    result = dict()
    for field in images.keys():
        main = 'images_{0}'.format(field)
        result[main] = images[field]
    return result


def get_others(items):
    """
    id: str，遊戲編號
    href: str，ex: /boardgame/205896/rising-sun
    name: str，遊戲名稱
    yearpublished: str
    minplayers: str
    maxplayers: str
    minplaytime: str
    maxplaytime: str
    minage: str
    short_description: str
    alternatenamescount: int，有幾種名稱，不同國家會有不同名稱
    description: str，含html tag，需解析
    topimageurl: str，遊戲主頁banner圖，ex: https://cf.geekdo-images.com/itemheader/img/FUK6onp6QGuQcN7E6V-sY7dADBk=/800x375/filters:quality(30)/pic3126430.jpg
    """
    result = dict()
    for field in ['id', 'name', 'yearpublished', 'minplayers', 'maxplayers', 'minplaytime', 'maxplaytime', 'minage', 'short_description', 'alternatenamescount', 'description', 'imageurl', 'topimageurl']:
        try:
            _check_field(field, field, items)
        except:
            raise

        if field == 'description':
            soup = BeautifulSoup(items[field], 'html.parser')
            items[field] = soup.get_text()
        result[field] = items[field]

    return result


def build_other_result(field_type, basic_info):
    result = dict()
    result['id'] = basic_info['bgid']

    if field_type == 'rank':
        pass
    elif field_type == 'poll':
        pass

    return result


def parse_geekitem_preload(data, bgid, store=None):
    items = data['item']
    # --- 主要資訊 ---
    # 沒有巢狀的欄位
    result = get_others(items)
    # 有額外資訊要來出來存放的
    rank_result, other_category_rank_results = get_rank_info(
        items)
    result.update(rank_result)
    # 沒有額外資訊要來出來存放的
    poll_result = get_polls(items)
    result.update(poll_result)
    stats_result = get_stats(items)
    result.update(stats_result)
    relatedcount_result = get_relatedcounts(items)
    result.update(relatedcount_result)
    linkcount_result = get_linkcounts(items)
    result.update(linkcount_result)
    store(result, 'basic')

    # --- 各類別資訊 ---
    # 在其他類別的排名
    for other_category_rank_result in other_category_rank_results:
        other_category_rank_result['bgid'] = bgid
        store(other_category_rank_result, 'rank')

    # 不同大小的遊戲圖
    images_result = get_images(items)
    store(images_result, 'images')

    # 遊戲機制、設計師、出版訊息、得過獎項、遊戲版本、擴充...都個個別存放一種類型的檔案
    links_results, links_require_fields = get_links(items)
    for links_require_field in links_require_fields:
        for links_result in links_results[links_require_field]:
            links_result['bgid'] = bgid
            store(links_result, links_require_field)
    # 各國桌遊名稱
    alternatenames_results = get_alternatenames(items)
    for alternatenames_result in alternatenames_results:
        alternatenames_result['bgid'] = bgid
        store(alternatenames_result, 'alternatenames')


def default_store(result, cnt):
    #print(result)
    return


def parse_web(data, store=default_store):
    scripts = []
    try:
        soup = BeautifulSoup(data, 'html.parser')
    except:
        raise
    else:
        scripts = soup.find_all('script')

    groups = None
    for script in scripts:
        script_string = str(script.string)

        # 注意：因為有使用到.format，所以如果search裡想要找的字符包含{ 或 } 時，記得要double字符
        groups = re.search(
            r'({0} *=) *(.+);'.format(DEFAULT_PRELOAD_INFO), script_string)
        if groups:
            break

    return groups.group(2)


def parse_api(data, store=default_store):
    return data


def connect_bgg(mainurls, bgid):
    connect_error = False
    error_msg = None

    result = dict()

    for url_type, mainurl in mainurls.items():
        connect_error = False
        error_msg = None
        if url_type == 'web':
            url = '{mainurl}/{bgid}'.format(mainurl=mainurl, bgid=bgid)
        elif url_type == 'api':
            url = '{mainurl}&objectid={bgid}'.format(mainurl=mainurl, bgid=bgid)

        logger.debug('{0}'.format(url))
        try:
            with urllib.request.urlopen(url, context=ctx) as fhand:
                    data = fhand.read()
        except HTTPError as e:
            error_msg = "{code}: {reason}({url})".format(
                code=e.code, reason=e.reason, url=url)
            connect_error = True
        except URLError as e:
            error_msg = e.reason
            connect_error = True
        except:
            error_msg = ','.join(sys.exc_info())
            connect_error = True

        if connect_error:
            raise BggConnectionError(error_msg, traceback.format_exc())
        else:
            result[url_type] = data

    return result

def get(mainurls, bgid, store=default_store):
    """
    先以web版撈到的script資訊為基底，再用bgg野生api的結果去更新，因為api版的每種結果筆數不限於6筆以內，所以可以完整補完網頁版的資訊
    """
    try:
        data = connect_bgg(mainurls, bgid)
    except:
        raise

    try:
        web_data = parse_web(data['web'])
        api_data = parse_api(data['api'])
    except:
        raise

    try:
        preload = json.loads(web_data)
    except json.decoder.JSONDecodeError:
        raise PreloadFormatError(
            '不是合法json格式', traceback.format_exc())
    except AttributeError:
        raise PreloadNotFound(
            '沒有結果回傳', traceback.format_exc())
    except:
        raise

    try:
        api_preload = json.loads(api_data)
    except json.decoder.JSONDecodeError:
        raise PreloadFormatError(
            '不是合法json格式', traceback.format_exc())
    except AttributeError:
        raise PreloadNotFound(
            '沒有結果回傳', traceback.format_exc())
    except:
        raise

    preload['item'].update(api_preload['item'])

    try:
        parse_geekitem_preload(preload, bgid, store)
    except:
        raise

if __name__ == '__main__':
    try:
        get({
            'web': 'https://boardgamegeek.com/boardgame',
            'api': 'https://api.geekdo.com/api/geekitems?nosession=1&objecttype=thing&subtype=boardgame'
        }, '205896')
    except Exception as e:
        logger.error(e.args)
