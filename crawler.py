from tool.bggapi import BGGAPI
import csv
from datetime import datetime

main = 'https://boardgamegeek.com/browse/boardgame/page'


def store(result, cnt):
    data_fields, data = list(zip(*list(result.items())))
    if cnt == 0:
        writer.writerow(data_fields)

    writer.writerow(data)

now = datetime.now()
date_time = now.strftime('%Y%m%d')
csvfile = open('{0}.csv'.format(date_time), 'a')
writer = csv.writer(csvfile)

api = BGGAPI()
print("共蒐集到 {0} 筆遊戲, 最後一頁為 {1}".format(*api.get_rank_list(main, 1, 2, store, 1 )))

csvfile.close()
