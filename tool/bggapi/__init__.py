from . import ranklist, bginfo
from tool.MyStorage import MyStorage
from tool.MyException.bgg import *

class BggCralwer:
    """
    2020/08/11: version 1.0
    """
    def __init__(self, store_config=None):
        """
        :param store_config: 儲存設定{store_mode, data_type, data_path, data_name}，file模式預設儲存csv，print模式預設直接輸出螢幕
        ::store_mode: 資料儲存方式，file/db/print，預設file
        ::data_type: 儲存格式，json/csv，預設csv
        """
        if not store_config:
            raise TypeError('__init__() missing 1 required positional argument: {field}'.format(field='store_config'))

        self.storeapi = MyStorage(store_config)
        self.storage = self.storeapi.get_storage()

    def get_rank_list(self, mainurl=None, startpage=1, endpage=1, interval=10):
        """
        :param mainurl: bgg排名頁面url
        :param startpage: 從哪一頁開始蒐集，預設從第1頁
        :param endpage: 蒐集到哪一頁結束，-1代表蒐集到底，預設到第1頁
        :param interval: 每幾秒發一次request，預設10秒
        :return: (cnt, page) => (總共蒐集到的遊戲數量, 蒐集到第幾頁)
        """

        # 由於環境變數預設值無法將float inf轉為int，所以-1先暫時代表無限，在這邊才轉成inf
        if endpage == -1:
            endpage = float('Inf')
        try:
            result = ranklist.get(mainurl, startpage, endpage,
                              self.storage, interval)
        except:
            raise
        finally:
            self.storeapi.close_storage()

        return result

    def get_bg_info(self, mainurl=None, bgid=None):
        try:
            bginfo.get(mainurl, bgid)
        except:
            raise
