import urllib.parse

from .http import get_json


def get_quote(symbol):
    encoded = urllib.parse.quote(symbol, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"
    data = get_json(url, headers={"User-Agent": "Mozilla/5.0"})
    meta = data["chart"]["result"][0]["meta"]
    price = meta["regularMarketPrice"]
    prev_close = meta["previousClose"]
    pct = (price - prev_close) / prev_close * 100
    return {"symbol": symbol, "price": price, "prev_close": prev_close, "pct": pct}
