class FeatureNotFound(Exception):
    """
    不存在的功能
    """
    pass

class BggConnectionError(Exception):
    """
    連線api失敗
    """
    pass

"""
ranklist
"""
class RankListFieldFormatError(Exception):
    """
    排名頁面欄位DOM結構不符合預期
    """
    pass
class RankListPageFormatError(Exception):
    """
    排名頁面的頁數按鈕格式不符合預期
    """
    pass


"""
bginfo
"""
class BgInfoLanguageDependenceUndefined(Exception):
    """
    尚未定義的語言依賴選項
    """
    pass
class BgInfoNotComplete(Exception):
    """
    桌遊主頁面的script所包含的訊息不如預期
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

