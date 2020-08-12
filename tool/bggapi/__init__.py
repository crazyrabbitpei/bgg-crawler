from . import ranklist

class BGGAPI:
    """
    2020/08/11: version 1.0
    """

    def __init__(self):
        """Constructor
        """

    def get_rank_list(self, mainurl=None, startpage=1, endpage=1, store=None, interval=10):
        """
        :param mainurl: bgg排名頁面url
        :param startpage: 從哪一頁開始蒐集，預設從第1頁
        :param endpage: 蒐集到哪一頁結束，-1代表蒐集到底，預設到第1頁
        :param store: 蒐集結果儲存函式
        :param interval: 每幾秒發一次request，預設10秒
        :return: (cnt, page) => (總共蒐集到的遊戲數量, 蒐集到第幾頁)
        """
        # 由於環境變數預設值無法將float inf轉為int，所以-1先暫時代表無限，在這邊才轉成inf
        if endpage == -1:
            endpage = float('Inf')

        return ranklist.get(mainurl, startpage, endpage, store, interval)
