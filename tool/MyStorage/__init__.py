import logging
from logging import Logger
from logging.handlers import TimedRotatingFileHandler
import sys
import os

import csv
import json
from datetime import datetime

from tool.MyException.bgg import *


class MyStorage:
    """儲存設定
    預設儲存到file裡，格式為csv，路徑為./data
    """
    STORE_MODES = ['file', 'print', 'db']
    DATA_TYPES = ['csv', 'json']
    DEFAULT_DATA_PATH = './data'
    DEFAULT_DATA_NAME = 'bgg'
    DEFAULT_DATA_TYPE = DATA_TYPES[0]
    store_config = {
        'data_path': DEFAULT_DATA_PATH,
        'data_name': DEFAULT_DATA_NAME,
        'data_type': DEFAULT_DATA_TYPE,  # csv/json/print
        'store_mode': 'file',  # file/print
        'storage': None  # 儲存函式
    }

    def __init__(self, store_config=None):
        """
        :param store_config: 儲存設定{store_mode, data_type, data_path, data_name}，file模式預設儲存csv，print模式預設直接輸出螢幕
        :store_mode: 資料儲存方式，file/db/print，預設file
        :data_type: store_mode為file時用到，儲存格式，json/csv，預設DATA_TYPES[0]
        :data_name: store_mode為file時用到，預設DEFAULT_DATA_NAME
        :data_path: store_mode為file時用到，預設DEFAULT_DATA_PATH
        """

        # ========= 儲存設定 =========
        if not store_config:
            raise TypeError('__init__() missing 1 required positional argument: {field}'.format(
                field='store_config'))

        self.store_config.update(store_config)

        try:
            self._check_config()
        except FeatureNotFound:
            raise
        except:
            raise
        else: # 根據儲存格式設定儲存函式
            self.store_config['storage'] = self._get_storage()

        # 創建儲存指標
        if self.store_config['store_mode'] == 'file':
            now = datetime.now()
            date_time = now.strftime('%Y%m%d')
            if not os.path.isdir(self.store_config['data_path']):
                os.mkdir(self.store_config['data_path'], 0o770)
            try:
                self.fhandle = open('{0}/{1}.{2}.{3}'.format(self.store_config['data_path'], self.store_config['data_name'],
                                                         date_time, self.store_config['data_type']), 'a')
            except FileNotFoundError:
                raise
            except:
                raise

            # 自動轉成csv格式的middleware，呼叫writer.writerow將陣列轉成csv寫入
            if self.store_config['data_type'] == 'csv':
                self.writer = csv.writer(self.fhandle)
        #elif self.store_config['store_mode'] == 'db':
        #    pass


    def _check_config(self):
        if self.store_config['store_mode'] not in self.STORE_MODES:
            raise FeatureNotFound(
                '資料儲存方式(store_mode)尚未定義: {0}'.format(self.store_config.get('store_mode', None)))
        if self.store_config['store_mode'] == 'file' and self.store_config['data_type'] not in self.DATA_TYPES:
            raise FeatureNotFound(
                '尚未定義的儲存格式(data_type): {0}'.format(self.store_config.get('data_type', None)))



    def _get_storage(self):
        store_mode = self.store_config['store_mode']
        data_type = self.store_config['data_type']
        if store_mode == 'file':
            if data_type == 'csv':
                return self.store_csv
            elif data_type == 'json':
                return self.store_json
        elif store_mode == 'print':
            return self.print_result
        # elif store_mode == 'db':
        #     pass
        else:
            return None

    def get_storage(self):
        return self.store_config['storage']

    def store_csv(self, data, cnt):
        value_fields, value = list(zip(*list(data.items())))
        if cnt == 0:
            self.writer.writerow(value_fields)
        self.writer.writerow(value)

    def store_json(self, data, cnt):
        json.dump(data, self.fhandle)
        self.fhandle.write('\n')

    def close_storage(self):
        try:
            self.fhandle.close()
        except:
            pass

    def print_result(self, data, cnt):
        print("第 {0} 筆: {1}".format(cnt, data))

