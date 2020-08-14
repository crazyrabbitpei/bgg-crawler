from tool.BggApi import BggCralwer
from tool.MyLogger import MyLogger

import csv
from datetime import datetime
import math
import logging
from logging.handlers import TimedRotatingFileHandler
import os

logger = MyLogger(log_path='./logs', log_file='{0}.log'.format(__name__), name=__name__)
RANK_URL = 'https://boardgamegeek.com/browse/boardgame/page'

def main():
    crawler = BggCralwer(store_config={'store_mode': 'file', 'data_type': 'csv', 'data_path': './data', 'data_name': 'rank_list'})
    logger.info("共蒐集到 {0} 筆遊戲, 最後一頁為 {1}".format( *crawler.get_rank_list(mainurl=RANK_URL, startpage=int(os.getenv('RANK_PAGE_FROM', 1)), endpage=int(os.getenv('RANK_PAGE_TO', 1)), interval=int(os.getenv('INTERVAL', 1)))))


if __name__ == '__main__':
    main()
