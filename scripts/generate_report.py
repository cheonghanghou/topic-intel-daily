import html as html_lib
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.emailer import send_email
from lib.sources import fetch_all
from lib.textmatch import any_keyword, dedupe, has_stat, is_ad_or_noise
from lib.yahoo import get_quote

NY = ZoneInfo("America/New_York")

DATA_INDUSTRY_KEYWORDS = [
    "数据要素", "大数据", "数据分析", "数字经济", "人工智能", "AI", "大模型", "数据安全",
    "云计算", "数据治理", "算力", "芯片", "半导体", "机器人", "自动驾驶",
]
FINANCE_KEYWORDS = [
    "股市", "A股", "美股", "港股", "基金", "债券", "汇率", "黄金", "原油", "IPO", "财报",
    "并购", "估值", "央行", "降息", "降准", "利率", "理财", "保险", "信贷",
]
POLICY_KEYWORDS = [
    "发改委", "证监会", "国务院", "政策", "新规", "办法", "通知", "监管", "财政部",
    "关税", "GDP", "CPI", "PPI", "银保监会",
]
RELEVANCE_KEYWORDS = DATA_INDUSTRY_KEYWORDS + FINANCE_KEYWORDS + POLICY_KEYWORDS

HOT_SOURCES = {"微博热搜", "百度热搜"}
STAT_ELIGIBLE_SOURCES = {"36氪", "华尔街见闻", "财联社", "金十数据"}

COMPANY_TICKERS = {
    "英伟达": "NVDA",
    "苹果": "AAPL",
    "特斯拉": "TSLA",
    "台积电": "TSM",
    "阿里巴巴": "BABA",
    "阿里": "BABA",
    "腾讯": "0700.HK",
    "宁德时代": "300750.SZ",
    "三星": "005930.KS",
    "港交所": "0388.HK",
    "微软": "MSFT",
    "谷歌": "GOOGL",
    "亚马逊": "AMZN",
    "Meta": "META",
    "百度": "BIDU",
    "京东": "JD",
    "拼多多": "PDD",
    "小米": "1810.HK",
    "比亚迪": "1211.HK",
}


def clean_items(items):
    items = [i for i in items if i.get("title") and not is_ad_or_noise(i["title"] + i.get("summary", ""))]
    return dedupe(items)


def build_sections(items):
    claimed = set()

    def fp(item):
        return item["title"][:16]

    stat_section = []
    for item in items:
        if item["source"] in STAT_ELIGIBLE_SOURCES and has_stat(item["title"] + item.get("summary", "")):
            key = fp(item)
            if key not in claimed:
                claimed.add(key)
                stat_section.append(item)

    hot_section = []
    for item in items:
        key = fp(item)
        if key in claimed:
            continue
        if item["source"] in HOT_SOURCES and any_keyword(item["title"], RELEVANCE_KEYWORDS):
            claimed.add(key)
            hot_section.append(item)

    if len(hot_section) < 3:
        for item in items:
            key = fp(item)
            if key in claimed:
                continue
            if item["source"] == "36氪":
                claimed.add(key)
                hot_section.append(item)
            if len(hot_section) >= 5:
                break

    trend_section = []
    for item in items:
        key = fp(item)
        if key in claimed:
            continue
        if item["source"] == "36氪" or any_keyword(item["title"] + item.get("summary", ""), RELEVANCE_KEYWORDS):
            claimed.add(key)
            trend_section.append(item)

    return hot_section[:8], trend_section[:12], stat_section[:10]


def build_stock_section(items):
    mentions = {}
    for item in items:
        text = item["title"] + item.get("summary", "")
        for name, ticker in COMPANY_TICKERS.items():
            if name not in text:
                continue
            entry = mentions.setdefault(ticker, {"name": name, "titles": [], "count": 0})
            entry["count"] += 1
            if item["title"] not in entry["titles"]:
                entry["titles"].append(item["title"])

    results = []
    for ticker, info in mentions.items():
        try:
            q = get_quote(ticker)
        except Exception as e:
            print(f"[warn] quote fetch failed for {ticker}: {e}")
            continue
        pct = q["pct"]
        if abs(pct) >= 2:
            reco = "重点关注：股价大幅波动"
        elif abs(pct) >= 1:
            reco = "建议关注：股价有一定波动"
        elif info["count"] >= 2:
            reco = "建议关注：多条新闻提及"
        else:
            reco = "一般关注"
        results.append(
            {
                "name": info["name"],
                "ticker": ticker,
                "price": q["price"],
                "pct": pct,
                "count": info["count"],
                "titles": info["titles"][:3],
                "reco": reco,
            }
        )

    results.sort(key=lambda r: abs(r["pct"]), reverse=True)
    return results[:8]


def render_html(date_str, hot, trend, stat, stocks):
    def item_html(item):
        title = html_lib.escape(item["title"])
        source = html_lib.escape(item["source"])
        url = html_lib.escape(item.get("url", ""))
        summary = html_lib.escape(item.get("summary", ""))
        summary_html = f'<p class="summary">{summary}</p>' if summary else ""
        link_open = f'<a href="{url}" target="_blank">' if url else ""
        link_close = "</a>" if url else ""
        return f"""
        <li>
          <span class="source">{source}</span>
          <div class="title">{link_open}{title}{link_close}</div>
          {summary_html}
        </li>"""

    def section_html(title, items):
        if not items:
            body = '<li class="empty">今日暂无相关内容</li>'
        else:
            body = "".join(item_html(i) for i in items)
        return f"""
      <section>
        <h2>{title}</h2>
        <ul>{body}</ul>
      </section>"""

    def stock_item_html(s):
        name = html_lib.escape(s["name"])
        ticker = html_lib.escape(s["ticker"])
        pct = s["pct"]
        pct_class = "up" if pct >= 0 else "down"
        pct_str = f"{'+' if pct >= 0 else ''}{pct:.2f}%"
        reco = html_lib.escape(s["reco"])
        titles = "、".join(html_lib.escape(t) for t in s["titles"])
        return f"""
        <li>
          <div class="stock-row">
            <span class="stock-name">{name} <span class="ticker">{ticker}</span></span>
            <span class="stock-price">{s['price']:.2f} <span class="pct {pct_class}">{pct_str}</span></span>
          </div>
          <p class="reco">{reco}（相关报道 {s['count']} 条）</p>
          <p class="summary">相关新闻：{titles}</p>
        </li>"""

    def stock_section_html(items):
        if not items:
            body = '<li class="empty">今日暂无明显相关标的</li>'
        else:
            body = "".join(stock_item_html(i) for i in items)
        return f"""
      <section>
        <h2>四、相关股票行情与关注建议</h2>
        <ul>{body}</ul>
      </section>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>选题情报 | {date_str}</title>
<style>
  body {{
    font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
    background: #f5f5f7;
    color: #1d1d1f;
    margin: 0;
    padding: 40px 20px;
  }}
  .container {{
    max-width: 760px;
    margin: 0 auto;
  }}
  h1 {{
    font-size: 28px;
    margin-bottom: 4px;
  }}
  .date {{
    color: #86868b;
    margin-bottom: 32px;
    font-size: 14px;
  }}
  section {{
    background: #fff;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  }}
  h2 {{
    font-size: 18px;
    border-left: 4px solid #0071e3;
    padding-left: 10px;
    margin-top: 0;
  }}
  ul {{
    list-style: none;
    padding: 0;
    margin: 0;
  }}
  li {{
    padding: 12px 0;
    border-bottom: 1px solid #e5e5e7;
  }}
  li:last-child {{
    border-bottom: none;
  }}
  li.empty {{
    color: #86868b;
    font-size: 14px;
  }}
  .source {{
    display: inline-block;
    font-size: 12px;
    color: #0071e3;
    background: #eaf3ff;
    border-radius: 6px;
    padding: 2px 8px;
    margin-bottom: 6px;
  }}
  .title {{
    font-size: 15px;
    line-height: 1.5;
  }}
  .title a {{
    color: #1d1d1f;
    text-decoration: none;
  }}
  .title a:hover {{
    text-decoration: underline;
  }}
  .summary {{
    font-size: 13px;
    color: #6e6e73;
    margin: 6px 0 0;
    line-height: 1.5;
  }}
  .stock-row {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    font-size: 15px;
  }}
  .stock-name {{
    font-weight: 600;
  }}
  .ticker {{
    font-weight: 400;
    color: #86868b;
    font-size: 12px;
  }}
  .stock-price {{
    font-weight: 600;
  }}
  .pct {{
    font-size: 13px;
    margin-left: 4px;
  }}
  .pct.up {{
    color: #d9363e;
  }}
  .pct.down {{
    color: #1a9850;
  }}
  .reco {{
    font-size: 13px;
    color: #0071e3;
    margin: 6px 0 0;
    font-weight: 500;
  }}
</style>
</head>
<body>
  <div class="container">
    <h1>选题情报</h1>
    <div class="date">{date_str}｜数据行业 · 金融行业 24小时动态</div>
    {section_html("一、今日热点选题", hot)}
    {section_html("二、行业趋势速览", trend)}
    {section_html("三、核心数据汇总", stat)}
    {stock_section_html(stocks)}
  </div>
</body>
</html>"""


def render_plain_text(date_str, hot, trend, stat, stocks):
    def fmt_list(items):
        if not items:
            return "1. 今日暂无相关内容"
        lines = []
        for i, item in enumerate(items, 1):
            line = f"{i}. {item['title']}（来源：{item['source']}）"
            if item.get("url"):
                line += f"\n   链接：{item['url']}"
            lines.append(line)
        return "\n".join(lines)

    def fmt_stocks(items):
        if not items:
            return "1. 今日暂无明显相关标的"
        lines = []
        for i, s in enumerate(items, 1):
            pct_str = f"{'+' if s['pct'] >= 0 else ''}{s['pct']:.2f}%"
            lines.append(
                f"{i}. {s['name']}（{s['ticker']}）：{s['price']:.2f}（{pct_str}）— {s['reco']}（相关报道{s['count']}条）\n"
                f"   相关新闻：{'、'.join(s['titles'])}"
            )
        return "\n".join(lines)

    return f"""【选题情报｜{date_str}】

一、今日热点选题
{fmt_list(hot)}

二、行业趋势速览
{fmt_list(trend)}

三、核心数据汇总
{fmt_list(stat)}

四、相关股票行情与关注建议
{fmt_stocks(stocks)}
"""


def main():
    now = datetime.now(NY)
    date_str = now.strftime("%Y-%m-%d")

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    html_path = os.path.join(base_dir, "选题情报.html")
    archive_path = os.path.join(base_dir, "reports", f"{date_str}.html")

    force = os.environ.get("FORCE_RUN") == "true"
    if not force and now.hour != 7:
        print(f"当前纽约时间 {now.strftime('%Y-%m-%d %H:%M')}，不在7点触发窗口内，退出。")
        return
    if os.path.exists(archive_path):
        print(f"{date_str} 的选题情报已存在，跳过重复生成。")
        return

    gmail_addr = os.environ["GMAIL_ADDRESS"]
    gmail_pass = os.environ["GMAIL_APP_PASSWORD"]

    items = clean_items(fetch_all(hours=24))
    hot, trend, stat = build_sections(items)
    stocks = build_stock_section(items)

    html_content = render_html(date_str, hot, trend, stat, stocks)
    text_content = render_plain_text(date_str, hot, trend, stat, stocks)

    os.makedirs(os.path.dirname(archive_path), exist_ok=True)
    with open(archive_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    send_email(f"【选题情报｜{date_str}】", text_content, gmail_addr, gmail_pass)
    print(f"选题情报已生成并发送：{archive_path}")


if __name__ == "__main__":
    main()
