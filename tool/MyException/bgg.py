class FeatureNotFound(Exception):
    """
    不存在的功能
    """
    pass

class PreloadNotFound(Exception):
    """
    bginfo.py蒐集結果裡的script中沒有預期的桌遊資訊參數
    """
    pass

class PreloadFormatError(Exception):
    """
    bginfo.py蒐集結果裡的script裡的桌遊資訊的json格式不完整
    """
    pass

class BggConnectionError(Exception):
    """
    連線api失敗
    """
    pass


class RankListPageFormatError(Exception):
    """
    排名頁面的頁數按鈕格式不符合預期
    """
    pass
