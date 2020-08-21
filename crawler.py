from tool.BggApi import BggCralwer
from tool.MyLogger import MyLogger
from tool.MyException.bgg import *
import csv
from datetime import datetime
import math
import logging
from logging.handlers import TimedRotatingFileHandler
import os, sys, traceback, time
import pandas as pd
from manage_data import DataManage


logger = MyLogger(log_path='./logs', log_file='{0}.log'.format(__name__), name=__name__)

def test_rank_list():
    logger.info("共蒐集到 {0} 筆遊戲, 最後一頁為 {1}".format(*crawler.get_rank_list(startpage=int(os.getenv(
        'RANK_PAGE_FROM', 1)), endpage=int(os.getenv('RANK_PAGE_TO', 1)), interval=int(os.getenv('INTERVAL', 1)))))


def test_bg_info(bgids, interval=int(os.getenv('INTERVAL', 3))):
    try:
        for bgid in bgids:
            logger.debug('Start {0}'.format(bgid))
            crawler.get_bg_info(bgid)
            time.sleep(interval)
    except (BgInfoLanguageDependenceUndefined, BgInfoNotComplete, PreloadNotFound, PreloadFormatError) as e:
        raise Exception(bgid, *e.args)
    except Exception as e:
        raise
    finally:
        crawler.storeapi.close_storage()


def read_bgid_list(id_field_name, tname, limit=100):
    return data_manage.get_bg_ids_from_rank(id_field_name, tname, limit)

def link_to_db(dbname):
    return DataManage(dbname)

if __name__ == '__main__':
    crawler = BggCralwer(store_config={
                         'store_mode': 'file', 'data_type': 'csv', 'data_path': './data', 'data_name': 'test'})
    dbname = sys.argv[1]
    tname = sys.argv[2]
    id_field_name = sys.argv[3]
    # 一次拿取多少筆bg id來蒐集
    limit = sys.argv[4]

    data_manage = link_to_db(dbname)
    ids = read_bgid_list(id_field_name, tname, limit)
    try:
        #test_rank_list()
        test_bg_info(ids)
    except BggConnectionError as e:
        logger.error(e.args)
    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(e.args)

    data_manage.close_connection()
