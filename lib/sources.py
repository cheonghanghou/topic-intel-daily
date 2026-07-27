import re
import time
import xml.etree.ElementTree as ET

from .http import get_json, get_text

NEWSNOW_BASE = "https://newsnow.busiyi.world/api/s"


def fetch_36kr(hours=24):
    xml_text = get_text("https://36kr.com/feed")
    root = ET.fromstring(xml_text)
    cutoff = time.time() - hours * 3600
    items = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date_raw = (item.findtext("pubDate") or "").strip()
        desc = re.sub("<[^>]+>", "", item.findtext("description") or "")
        desc = re.sub(r"\s+", " ", desc).strip()[:200]
        ts = _parse_36kr_date(pub_date_raw)
        if ts is not None and ts < cutoff:
            continue
        items.append({"title": title, "url": link, "summary": desc, "source": "36氪", "ts": ts})
    return items


def _parse_36kr_date(raw):
    try:
        t = time.strptime(raw[:19], "%Y-%m-%d %H:%M:%S")
        return time.mktime(t)
    except Exception:
        return None


def fetch_newsnow(source_id, label):
    data = get_json(f"{NEWSNOW_BASE}?id={source_id}")
    items = []
    for item in data.get("items", []):
        title = (item.get("title") or "").strip()
        url = item.get("url") or ""
        extra = item.get("extra") or {}
        pub_date = item.get("pubDate")
        ts = None
        if isinstance(pub_date, (int, float)):
            ts = pub_date / 1000 if pub_date > 10**12 else pub_date
        elif isinstance(extra.get("date"), (int, float)):
            d = extra["date"]
            ts = d / 1000 if d > 10**12 else d
        items.append({"title": title, "url": url, "summary": "", "source": label, "ts": ts})
    return items


def fetch_all(hours=24):
    all_items = []
    all_items.extend(fetch_36kr(hours=hours))

    for source_id, label in [
        ("wallstreetcn", "华尔街见闻"),
        ("cls", "财联社"),
        ("jin10", "金十数据"),
    ]:
        try:
            items = fetch_newsnow(source_id, label)
            cutoff = time.time() - hours * 3600
            items = [i for i in items if i["ts"] is None or i["ts"] >= cutoff]
            all_items.extend(items)
        except Exception as e:
            print(f"[warn] fetch {label} failed: {e}")

    for source_id, label in [("weibo", "微博热搜"), ("baidu", "百度热搜")]:
        try:
            all_items.extend(fetch_newsnow(source_id, label))
        except Exception as e:
            print(f"[warn] fetch {label} failed: {e}")

    return all_items
