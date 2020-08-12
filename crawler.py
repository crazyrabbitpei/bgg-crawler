from tool.bggapi import BGGAPI
import csv
from datetime import datetime
import math
import logging
from logging.handlers import TimedRotatingFileHandler

url = 'https://boardgamegeek.com/browse/boardgame/page'

csvfile = None
writer = None

def store(result, cnt):
    data_fields, data = list(zip(*list(result.items())))
    if cnt == 0:
        writer.writerow(data_fields)

    writer.writerow(data)

def set_logger():
    logging.basicConfig(filename='{0}/{1}.log'.format('./logs', 'main'), format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)

    # logger = logging.getLogger("main")
    # fhandle = TimedRotatingFileHandler(
    #     '{0}/{1}.log'.format('./logs', 'main'), when='D', interval=1, backupCount=3)
    # fhandle.suffix = '%Y%m%d'

    # formatter = logging.Formatter(
    #     '%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    # fhandle.setFormatter(formatter)
    # fhandle.setLevel(logging.DEBUG)

    # logger.addHandler(fhandle)
    # return logger
    return



def main():
    set_logger()

    api = BGGAPI()
    logging.info("共蒐集到 {0} 筆遊戲, 最後一頁為 {1}".format(
        *api.get_rank_list(mainurl=url, startpage=1, endpage=float('Inf'), store=store, interval=1)))

    if csvfile:
        csvfile.close()

if __name__ == '__main__':
    now = datetime.now()
    date_time = now.strftime('%Y%m%d')
    csvfile = open('{0}.csv'.format(date_time), 'a')
    writer = csv.writer(csvfile)

    main()
