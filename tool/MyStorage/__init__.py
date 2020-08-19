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

    # db儲存指標
    dbhandle = None

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

        # 創建儲存資料夾
        if self.store_config['store_mode'] == 'file':
            if not os.path.isdir(self.store_config['data_path']):
                os.mkdir(self.store_config['data_path'], 0o770)
            # 初始儲存指標和相關控制參數
            self._init_store_process()

    def _is_available_file_data_type(self):
        if self.store_config['data_type'] not in self.DATA_TYPES:
            return False
        return True
    def _check_config(self):
        if self.store_config['store_mode'] not in self.STORE_MODES:
            raise FeatureNotFound(
                '資料儲存方式(store_mode)尚未定義: {0}'.format(self.store_config.get('store_mode', None)))
        if self.store_config['store_mode'] == 'file' and not self._is_available_file_data_type():
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

    def _init_store_process(self, date_time=None):
        """
        - 關閉所有現有檔案
        - 初始檔案儲存所需要的變數
        - 更新當前檔案日期戳記
        """
        # 有舊的檔案要關閉，date_time為新的日期戳記
        if date_time:
            self.close_storage()

        self.writer = self.fhandle = None
        self.multi_handles = dict()
        self.multi_writers = dict() # csv儲存用

        self.csv_result_need_field_header = dict()

        self.cur_file_date = date_time
        self.cur_full_file_name = None # 完整儲存路徑和檔名

    def _need_create_store_point(self, fname):
        """
        判定什麼情況要創建儲存指標
        """
        # 還沒初始寫入指標
        if not self.fhandle:
            return True
        # 尚未創建結果檔案
        elif not self._store_file_exist():
            return True
        # 已有結果檔案在硬碟中，但是尚未建立儲存指鏢
        elif fname not in self.multi_handles:
            return True

        return False

    def _store_file_exist(self):
        if os.path.isfile(self.cur_full_file_name):
            return True
        return False
    def _check_store_pointer(self, file_name=None):
        """
        指定當前要儲存的指標
        """
        now = datetime.now()
        date_time = now.strftime('%Y%m%d')
        if file_name:
            fname = '{0}.{1}.{2}'.format(
                file_name, date_time, self.store_config['data_type'])
        else:
            fname = '{0}.{1}.{2}'.format(
                self.store_config['data_name'], date_time, self.store_config['data_type'])

        # 不同日所蒐集到的資料，舊日期資料全數關閉
        if self.cur_file_date != date_time:
            self._init_store_process(date_time)

        self.cur_full_file_name = '{0}/{1}'.format(self.store_config
        ['data_path'], fname)

        if not self._store_file_exist():
            self.csv_result_need_field_header[fname] = True
        else:
            self.csv_result_need_field_header[fname] = False

        # 創建/指定當前儲存指標
        if self._need_create_store_point(fname):
            try:
                self.fhandle = open(self.cur_full_file_name, 'a', newline='')
            except FileNotFoundError:
                raise
            except:
                raise
            else:
                self.multi_handles[fname] = self.fhandle

                #print(type(self.fhandle))
                #print('{0}: {1}/{2}'.format(fname, id(self.multi_handles[fname]), id(self.fhandle)))

        else:
            #print('read before=> {0}: {1}/{2}'.format(fname, id(self.multi_handles[fname]), id(self.fhandle)))
            self.fhandle = self.multi_handles[fname]
            #print('read after=> {0}: {1}/{2}'.format(fname, id(self.multi_handles[fname]), id(self.fhandle)))

        # 創建/指定當前csv儲存指標
        if self.store_config['data_type'] == 'csv':
            if fname in self.multi_writers:
                self.writer = self.multi_writers[fname]
            else:
                self.writer = csv.writer(self.fhandle)
                self.multi_writers[fname] = self.writer
        return fname

    def store_csv(self, data, file_name=None):
        """
        :param plain_csv: 是否為csv str
        """
        fname = self._check_store_pointer(file_name)
        value_fields, value = list(zip(*list(data.items())))
        if self.csv_result_need_field_header[fname]:
            self.writer.writerow(value_fields)
            self.csv_result_need_field_header[fname] = False

        self.writer.writerow(value)

    def store_json(self, data, file_name=None):
        self._check_store_pointer(file_name)

        json.dump(data, self.fhandle)
        self.fhandle.write('\n')

    def close_storage(self):
        if not self.multi_handles: pass

        for fname in self.multi_handles.keys():
            try:
                self.multi_handles[fname].close()
                #print('close => {0}: {1}/{2}'.format(fname, id(self.multi_handles[fname]), id(self.fhandle)))

            except:
                pass

    def print_result(self, data, data_type='bgg'):
        print("{0} => {2}".format(data_type, data))

