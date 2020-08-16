from tool.BggApi import BggCralwer
from tool.MyLogger import MyLogger
from tool.MyException.bgg import BggConnectionError, RankListPageFormatError

import csv
from datetime import datetime
import math
import logging
from logging.handlers import TimedRotatingFileHandler
import os, sys

logger = MyLogger(log_path='./logs', log_file='{0}.log'.format(__name__), name=__name__)

def test_rank_list(url):
    logger.info("共蒐集到 {0} 筆遊戲, 最後一頁為 {1}".format(*crawler.get_rank_list(mainurl=url, startpage=int(os.getenv(
        'RANK_PAGE_FROM', 1)), endpage=int(os.getenv('RANK_PAGE_TO', 1)), interval=int(os.getenv('INTERVAL', 1)))))

def test_bg_info(url, bgid):
    crawler.get_bg_info(url, bgid)
    pass

if __name__ == '__main__':
    crawler = BggCralwer(store_config={
                         'store_mode': 'file', 'data_type': 'csv', 'data_path': './data', 'data_name': 'test'})
    try:
        #test_rank_list('https://boardgamegeek.com/browse/boardgame/page')
        test_bg_info('https://boardgamegeek.com/boardgame', '205896')
    except SyntaxError as e:
        logger.error(e)
    except BggConnectionError as e:
        logger.error(e)
    except RankListPageFormatError as e:
        logger.error(e)
    except:
        logger.error(sys.exc_info())
