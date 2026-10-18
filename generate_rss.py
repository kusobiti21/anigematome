"""
記事ファイル(article*.html)から RSS フィード(rss.xml)を作るスクリプト。
アンテナサイトやフィードリーダーが、新しい記事を見つけるために使う。
"""

import glob
import html as html_lib
import re
from datetime import datetime, timedelta, timezone

SITE_TITLE = "アニゲーまとめ！"
SITE_LINK = "https://heartfelt-taiyaki-7783f9.netlify.app/"
SITE_DESCRIPTION = "ゲーム・アニメの話題を2ch・5chからまとめてお届けするまとめサイト"
SITE_LANGUAGE = "ja"
OUTPUT_PATH = "rss.xml"
JST = timezone(timedelta(hours=9))


def article_number(path):
    m = re.search(r"article(\d+)\.html$", path)
    return int(m.group(1)) if m else 0


def clean_text(fragment):
    text = re.sub(r"<.*?>", "", fragment, flags=re.S)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def extract_articles():
    articles = []
    for path in sorted(glob.glob("article*.html"), key=article_number):
        with open(path, encoding="utf-8") as f:
            content = f.read()

        title_match = re.search(r"<h1[^>]*>(.*?)</h1>", content, re.S)
        meta_match = re.search(r'<div class="article-meta"[^>]*>(.*?)</div>', content, re.S)
        date_match = None
        if meta_match:
            date_match = re.search(
                r"(\d{4})/(\d{1,2})/(\d{1,2})(?:\s+(\d{1,2}):(\d{2}))?", meta_match.group(1)
            )
        lead_match = re.search(r'<p class="lead"[^>]*>(.*?)</p>', content, re.S)

        if not title_match or not date_match:
            print(f"[WARN] {path}: タイトルまたは日付が見つからずスキップしました")
            continue

        y, mo, d, hh, mm = date_match.groups()
        dt = datetime(int(y), int(mo), int(d), int(hh or 0), int(mm or 0), tzinfo=JST)

        articles.append({
            "path": path,
            "title": clean_text(title_match.group(1)),
            "lead": clean_text(lead_match.group(1)) if lead_match else "",
            "date": dt,
        })

    articles.sort(key=lambda a: (a["date"], article_number(a["path"])), reverse=True)
    return articles


def rfc822(dt):
    return dt.strftime("%a, %d %b %Y %H:%M:%S %z")


def escape(s):
    return html_lib.escape(s, quote=True)


def build_rss(articles):
    # 最終更新日時は一番新しい記事の日時にする(毎回中身が変わって無駄なコミットが出ないように)
    last_build = articles[0]["date"]

    items_xml = []
    for a in articles:
        link = SITE_LINK + a["path"]
        items_xml.append(f"""    <item>
      <title>{escape(a['title'])}</title>
      <link>{escape(link)}</link>
      <guid isPermaLink="true">{escape(link)}</guid>
      <pubDate>{rfc822(a['date'])}</pubDate>
      <description>{escape(a['lead'])}</description>
    </item>""")

    items_block = "\n".join(items_xml)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{escape(SITE_TITLE)}</title>
    <link>{escape(SITE_LINK)}</link>
    <atom:link href="{escape(SITE_LINK + 'rss.xml')}" rel="self" type="application/rss+xml" />
    <description>{escape(SITE_DESCRIPTION)}</description>
    <language>{SITE_LANGUAGE}</language>
    <lastBuildDate>{rfc822(last_build)}</lastBuildDate>
{items_block}
  </channel>
</rss>
"""


def main():
    articles = extract_articles()
    if not articles:
        print("[ERROR] 記事が1件も見つからなかったため、rss.xml を更新せず終了します。")
        return

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(build_rss(articles))

    print(f"[OK] {len(articles)}件の記事で {OUTPUT_PATH} を更新しました。")


if __name__ == "__main__":
    main()
