import base64
import os

CLOSE_APOSTROPHE = {'【', '】', '（', '）', '《', '》', '“', '”', '〔', '〕', '〈', '〉', '「', '」', '『', '』', '〖',
                    '〗'}  # ord大于256的闭合标点， '{', '}'不分全角半角，其ord小于256。


def rand_str(length: int) -> str:
    s = base64.b64encode(os.urandom(length)).decode("utf8")
    s = s.replace("\\", "").replace("/", "").replace("=", "").replace("+", "")
    return s



