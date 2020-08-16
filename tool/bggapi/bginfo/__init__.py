import urllib.request
from urllib.error import URLError, HTTPError
from bs4 import BeautifulSoup
import sys
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
fields = ['itemdata', 'relatedlinktypes', 'linkedforum_types', 'subtypename', 'rankinfo', 'polls', 'stats', 'relatedcounts', 'itemid', 'objecttype', 'objectid', 'label', 'labelpl', 'type', 'id', 'href', 'subtype', 'subtypes', 'versioninfo', 'name', 'alternatename', 'yearpublished', 'minplayers', 'maxplayers', 'minplaytime', 'maxplaytime', 'minage', 'override_rankable', 'targetco_url', 'walmart_id', 'instructional_videoid', 'summary_videoid', 'playthrough_videoid', 'focus_videoid', 'bggstore_product', 'short_description', 'links', 'linkcounts', 'secondarynamescount', 'alternatenamescount', 'primaryname', 'description', 'wiki', 'website', 'imageid', 'images', 'imagepagehref', 'imageurl', 'topimageurl', 'itemstate', 'promoted_ad', 'special_user', 'walmart_price']
"""
期望儲存欄位
"""
result_fields = ['rankinfo', 'polls', 'stats',
                 'relatedcounts', 'id', 'href', 'name', 'yearpublished', 'minplayers', 'maxplayers', 'minplaytime', 'maxplaytime', 'minage', 'short_description', 'links', 'linkcounts', 'alternatenamescount', 'description', 'images', 'imageurl', 'topimageurl', 'walmart_price']
"""
將巢狀裡的資訊解析出來
"""

nest_fields = {
    'rankinfo':{
        # 結果欄位名: {veryshortprettyname}_rank/baverage
        'fields': ['veryshortprettyname', 'rank', 'baverage']
    },
    'polls': {
        # 結果欄位名: polls_userplayers_(best/recommended)_(min/max)(若有多個list則拿取min/max都不為null的)、polls_userplayers_totalvotes、polls_(playerage/languagedependence)、polls_boardgameweight_(averageweight/votes)
        'fields': ['userplayers', 'playerage', 'languagedependence', 'boardgameweight'],
        'no_nest_fields': ['playerage', 'languagedependence'], # 直接拿取欄位值
        'has_nest_fields': {
            'userplayers': ['best', 'recommended', 'totalvotes'],
            'boardgameweight': ['averageweight', 'votes']
        }
    },
    'links': { # links: 每一子欄位應另存一份檔案，存入rdb時也該另開一個table
        'fields': ['boardgamedesigner', 'boardgameartist', 'boardgamepublisher', 'boardgamehonor', 'boardgamecategory', 'boardgamemechanic', 'boardgameexpansion', 'boardgameversion', 'boardgamefamily']
    },
    'stats': {
        # 結果欄位名: stats_{欄位名}
        'fields': []  # 空陣列代表全存
    },
    'relatedcounts': {
        # 結果欄位名: relatedcounts_{欄位名}
        'fields': [] # 空陣列代表全存
    },
    'linkcounts': {
        # 結果欄位名: linkcounts_{欄位名}
        'fields': []  # 空陣列代表全存
    },
    'images': {
        # 結果欄位名: images_{欄位名}
        'fields': ['thumb', 'square200', 'previewthumb']
    },
}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def check_field(main, items):
    if type(main) == list and len(items) > 0:
        for m in main:
            if m not in items[0]:
                raise BgInfoNotComplete('沒有 {0} 欄位'.format(main))
    elif main not in items:
        raise BgInfoNotComplete('沒有 {0} 欄位'.format(main))

def get_rank_info(items):
    """rankinfo: [{veryshortprettyname, rank, baverage}]
        - veryshortprettyname: Overall/Strategy...，排名種類
        - rank: str，在該種類的名次
        - beverage: str，geek rating
    """
    try:
        check_field('rankinfo', items)
    except:
        raise

    result = dict()
    # 每一個遊戲不一定都有同樣的類別排名，ex: family 或 strategy game的遊戲就會分別有family_rank和strategy_rank，匯進rdb時會出錯，所以這項資訊應該特別放一個table
    other_result = dict()

    for item in items['rankinfo']:
        main_name = '{veryshortprettyname}'.format(**item).lower()
        if main_name == 'overall':
            field_name = '{0}_rank'.format(main_name)
            result[field_name] = item['rank']
            field_name = '{0}_baverage'.format(main_name)
            result[field_name] = item['baverage']
        else:
            other_result[main_name] = item['rank']

    return (result, other_result)


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
        check_field('polls', items)
    except:
        raise

    result = dict()
    # languagedependence資訊會額外存放
    other_result = dict()

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
                '無法得到正確的polls_userplayers_{0}_min'.format(field))
        if not player_max:
            raise BgInfoNotComplete(
                '無法得到正確的polls_userplayers_{0}_max'.format(field))

    boardgameweight = polls['boardgameweight']
    for field in boardgameweight.keys():
        result['polls_boardgameweight_{0}'.format(
            field)] = boardgameweight[field]

    result['playerage'] = polls['playerage']
    other_result['languagedependence'] = polls['languagedependence']

    return (result, other_result)


def _get_links(main, items):
    result = []
    require_fields = ['name', 'objecttype', 'objectid']
    try:
        check_field(require_fields, items)
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
    """
    try:
        check_field('links', items)
    except:
        raise

    result = dict()
    require_fields = ['boardgamedesigner', 'boardgameartist', 'boardgamepublisher', 'boardgamehonor', 'boardgamecategory', 'boardgamemechanic', 'boardgameexpansion', 'boardgameversion', 'boardgamefamily']
    links = items['links']

    for field in require_fields:
        try:
            check_field(field, require_fields)
        except:
            raise

        result[field] = _get_links(field, links[field])

    return result

def get_stats(items):
    try:
        check_field('stats', items)
    except:
        raise

    stats = items['stats']
    result = dict()
    for field in stats.keys():
        main = 'stats_{0}'.format(field)
        result[main] = stats[field]
    return result


def get_relatedcounts():
    pass
def get_linkcounts():
    pass
def get_images():
    pass
def get_others():
    pass


def build_other_result(field_type, basic_info):
    result = dict()
    result['id'] = basic_info['bgid']

    if field_type == 'rank':
        pass
    elif field_type == 'poll':
        pass

    return result

def parse_geekitem_preload(data, bgid):
    """
    stats: {'usersrated', 'average', 'baverage', 'stddev', 'avgweight', 'numweights', 'numgeeklists', 'numtrading', 'numwanting', 'numwish', 'numowned', 'numprevowned', 'numcomments', 'numwishlistcomments', 'numhasparts', 'numwantparts', 'views', 'playmonth', 'numplays', 'numplays_month', 'numfans'}，numfans為int，其餘都為str
        - average: 玩家總平均
        - baverage: geek總平均
    relatedcounts: {'news', 'blogs', 'weblink', 'podcast'}，都為int
    objectid: int，遊戲編號
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
    linkcounts: {'boardgamedesigner', 'boardgameartist', 'boardgamepublisher', 'boardgamehonor', 'boardgamecategory', 'boardgamemechanic', 'boardgameexpansion', 'boardgameversion', 'expandsboardgame', 'boardgameintegration', 'contains', 'containedin', 'reimplementation', 'reimplements', 'boardgamefamily', 'videogamebg', 'boardgamesubdomain', 'boardgameaccessory', 'commerceweblink'}，都是int
    alternatenamescount: int，有幾種名稱，不同國家會有不同名稱
    description: str，含html tag，需解析
    images: {thumb, square200, previewthumb}，由小到大張遊戲圖片link，ex: https://cf.geekdo-images.com/thumb/img/SJV333FxGVxsOc2XYvtVYx-uMDU=/fit-in/200x150/pic3880340.jpg
    imageurl: str，遊戲圖片，ex: https://cf.geekdo-images.com/itemrep/img/7KmSH1xYiDDOcIQptnQoXSeOfLU=/fit-in/246x300/pic3880340.jpg
    topimageurl: str，遊戲主頁banner圖，ex: https://cf.geekdo-images.com/itemheader/img/FUK6onp6QGuQcN7E6V-sY7dADBk=/800x375/filters:quality(30)/pic3126430.jpg
    walmart_price: str，當前有登廣告的商家價格，ex: $79.99
    """
    result = dict()
    items = data['item']

    # 主要資訊
    rank_result, other_rank_result = get_rank_info(
        items)  # (result, other_rank_result)
    result.update(rank_result)
    poll_result, other_poll_result = get_polls(items)
    result.update(poll_result)
    stats_result = get_stats(items)
    result.update(stats_result)

    print(result)

    # 要分別存的資訊
    links_result = get_links(items)



    # 將不適合進rdb的或想額外建一個table的資訊再個別加上基本桌遊資訊以便匯入rdb
    other_poll_result.update(build_other_result('poll', {'bgid': bgid}))
    other_rank_result.update(build_other_result('rank', {'bgid': bgid}))


    print(other_poll_result)
    print(other_rank_result)
    print(links_result)




def get(mainurl, bgid):
    connect_error = False
    error_msg = None
    #url = '{mainurl}&objectid={bgid}'.format(mainurl=mainurl, bgid=bgid)
    url = '{mainurl}/{bgid}'.format(mainurl=mainurl, bgid=bgid)
    logger.debug('{0}'.format(url))

    scripts = []
    try:
        with urllib.request.urlopen(url, context=ctx) as fhand:
            data = fhand.read()
            soup = BeautifulSoup(data, 'html.parser')
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
    else:
        scripts = soup.find_all('script')

    groups = None
    for script in scripts:
        script_string = str(script.string)

        # 注意：因為有使用到.format，所以如果search裡想要找的字符包含{ 或 } 時，記得要double字符
        groups = re.search(r'({0} *=) *(.+);'.format(DEFAULT_PRELOAD_INFO), script_string)
        if groups:
            break

    # 將script中的preload值parse成json
    preload = None
    try:
        preload = json.loads(groups.group(2))
    except json.decoder.JSONDecodeError as e:
        raise PreloadFormatError(
            '{0} 的值不是合法json格式'.format(DEFAULT_PRELOAD_INFO))
    except AttributeError as e:
        raise PreloadNotFound(
            'script中沒有預期的 {0} 參數'.format(DEFAULT_PRELOAD_INFO))

    if connect_error:
        raise BggConnectionError(error_msg)

    parse_geekitem_preload(preload, bgid)

if __name__ == '__main__':
    try:
        get(main, '205896')
    except:
        logger.error(sys.exc_info())
