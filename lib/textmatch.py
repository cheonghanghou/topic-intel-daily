import re

STAT_PATTERN = re.compile(
    r"(\d+(\.\d+)?%|\d+(\.\d+)?\s*(亿|万亿|万|美元|元|美金)|同比|环比|增长\d|下降\d|GDP|CPI|PPI)"
)

AD_KEYWORDS = [
    "直播带货", "秒杀", "优惠券", "限时折扣", "抽奖", "免费领", "扫码", "点击领取",
    "广告", "推广合作", "招商加盟", "下载注册送",
]


def any_keyword(text, keywords):
    return any(kw in text for kw in keywords)


def matching_keywords(text, keywords):
    return [kw for kw in keywords if kw in text]


def is_ad_or_noise(text):
    return any_keyword(text, AD_KEYWORDS)


def has_stat(text):
    return bool(STAT_PATTERN.search(text))


def dedupe(items, key_len=16):
    seen = set()
    result = []
    for item in items:
        title = item.get("title", "").strip()
        if not title:
            continue
        fingerprint = re.sub(r"[\s,，。！？!?、\"'\[\]【】]", "", title)[:key_len]
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        result.append(item)
    return result
