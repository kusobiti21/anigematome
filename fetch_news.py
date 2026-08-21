#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================
公式ニュースサイトのRSSから最新記事を取得し、threads.json を生成する
============================================================
対象サイト(いずれも「タイトル+リンクのRSS配信」を明示的に許可、
または前提としているサイトのみを選定しています):

  - 4Gamer.net (注目記事)   https://www.4gamer.net/rss/news_topics.xml
  - ファミ通.com            https://www.famitsu.com/rss/fcom_all.rdf
  - GameSpark               https://www.gamespark.jp/rss/index.rdf
  - コミックナタリー(アニメ/マンガ) https://natalie.mu/comic/feed/news

出力される threads.json はサイト本文をコピーせず、
「タイトル・リンク・出典名」のみを保持します(見出しの要約紹介)。
リンク先は必ず元記事(出典サイト)になります。

GitHub Actions から1時間おきに自動実行される想定。
============================================================
"""

import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# (フィードURL, カテゴリ, 出典名, 1フィードあたりの最大取得件数)
FEEDS = [
    ("https://www.4gamer.net/rss/news_topics.xml", "game", "4Gamer", 4),
    ("https://automaton-media.com/feed/", "game", "AUTOMATON", 4),
    ("https://www.gamespark.jp/rss/index.rdf", "game", "GameSpark", 3),
    ("https://natalie.mu/comic/feed/news", "anime", "コミックナタリー", 4),
]

MAX_TOTAL = 12
OUTPUT_PATH = "threads.json"
REQUEST_TIMEOUT = 30
# 一部サイトは "ボットらしいUser-Agent" を弾くため、一般的なブラウザに
# 近い名乗り方にしておく(取得するのは見出し+リンクのみ)。
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 "
    "AniGeMatomeBot/1.0 (+https://heartfelt-taiyaki-7783f9.netlify.app/about.html)"
)

NS_STRIP = re.compile(r"\{.*\}")


def local_tag(elem):
    return NS_STRIP.sub("", elem.tag)


def fetch_xml(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return resp.read()


def parse_feed(xml_bytes):
    """RSS 2.0 (<item> under <channel>) と RSS 1.0/RDF (<item> at root level)
    の両方に対応する簡易パーサー。"""
    root = ET.fromstring(xml_bytes)
    items = []
    for elem in root.iter():
        if local_tag(elem) == "item":
            title, link = None, None
            for child in elem:
                tag = local_tag(child)
                if tag == "title" and child.text:
                    title = child.text.strip()
                elif tag == "link":
                    link = (child.text or child.get("href") or "").strip()
            if title and link:
                items.append({"title": title, "url": link})
    return items


def build_threads():
    all_items = []
    for feed_url, category, source, limit in FEEDS:
        try:
            xml_bytes = fetch_xml(feed_url)
            items = parse_feed(xml_bytes)[:limit]
            for it in items:
                all_items.append({
                    "title": it["title"],
                    "url": it["url"],
                    "category": category,
                    "source": source,
                })
        except Exception as e:
            print(f"[WARN] {source} の取得に失敗しました: {e}", file=sys.stderr)
            continue

    all_items = all_items[:MAX_TOTAL]
    for i, item in enumerate(all_items, start=1):
        item["id"] = str(i)

    return all_items


def main():
    threads = build_threads()

    if not threads:
        print("[ERROR] 取得できた記事が0件のため、threads.json を更新せず終了します。", file=sys.stderr)
        sys.exit(1)

    data = {
        "updated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "threads": threads,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[OK] {len(threads)}件のニュースで {OUTPUT_PATH} を更新しました。")


if __name__ == "__main__":
    main()
