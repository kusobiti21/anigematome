"""
トップページ(index.html)の記事一覧を、article*.html から自動生成するスクリプト。

index.html の中の次の目印の間を、毎回まるごと書き換える:
  <!-- AUTO:CARDS:START --> 〜 <!-- AUTO:CARDS:END -->  … 新着のスレ(カード表示、最新3件)
  <!-- AUTO:LIST:START -->  〜 <!-- AUTO:LIST:END -->   … 新着記事一覧(全件、新しい順)
  <!-- AUTO:SIDE:START -->  〜 <!-- AUTO:SIDE:END -->   … サイドバーの最近の記事(最新5件)

記事ファイル側で読み取るもの:
  <h1>タイトル</h1>
  <div class="article-meta"> の中の <span class="tag game|anime"> と 日付(2026/10/18 または 2026/10/18 14:00)
  <div class="res"> … 1つ目と2つ目をカードのプレビューに使う。件数はコメント数として表示
  <meta name="keywords" content="..."> (任意) … アフィリエイト商品の自動選択に使う
"""

import glob
import html as html_lib
import os
import re
from datetime import datetime

INDEX_PATH = "index.html"
CARD_COUNT = 3
LIST_COUNT = 30
SIDE_COUNT = 5
PREVIEW_COUNT = 2
PREVIEW_MAX_CHARS = 70

DEFAULT_KEYWORDS = {
    "game": "新作ゲーム,PS5",
    "anime": "アニメ,原作漫画",
}
CATEGORY_LABEL = {"game": "ゲーム", "anime": "アニメ"}
THUMB_ICON = {"game": "🎮", "anime": "📺"}
THUMB_COLORS = ["tb-blue", "tb-pink", "tb-green"]


def clean_text(fragment):
    text = re.sub(r"<.*?>", "", fragment, flags=re.S)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def esc(s):
    return html_lib.escape(s, quote=True)


def article_number(path):
    m = re.search(r"article(\d+)\.html$", path)
    return int(m.group(1)) if m else 0


def parse_article(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()

    title_m = re.search(r"<h1[^>]*>(.*?)</h1>", content, re.S)
    meta_m = re.search(r'<div class="article-meta"[^>]*>(.*?)</div>', content, re.S)
    if not title_m or not meta_m:
        print(f"[WARN] {path}: タイトルか article-meta が見つからないためスキップしました")
        return None

    meta = meta_m.group(1)
    date_m = re.search(r"(\d{4})/(\d{1,2})/(\d{1,2})(?:\s+(\d{1,2}):(\d{2}))?", meta)
    if not date_m:
        print(f"[WARN] {path}: 日付が見つからないためスキップしました")
        return None

    y, mo, d, hh, mm = date_m.groups()
    has_time = hh is not None
    dt = datetime(int(y), int(mo), int(d), int(hh or 0), int(mm or 0))

    category = "anime" if re.search(r'class="tag anime"', meta) else "game"

    res_blocks = re.findall(r'<div class="res"[^>]*>(.*?)</div>', content, re.S)
    previews = []
    for block in res_blocks:
        no_m = re.search(r'<span class="res-no"[^>]*>(.*?)</span>', block, re.S)
        no = clean_text(no_m.group(1)) if no_m else ""
        body = re.sub(r'<span class="res-no"[^>]*>.*?</span>', "", block, count=1, flags=re.S)
        text = clean_text(body)
        if not text:
            continue
        if len(text) > PREVIEW_MAX_CHARS:
            text = text[:PREVIEW_MAX_CHARS] + "…"
        previews.append((no, text))
        if len(previews) >= PREVIEW_COUNT:
            break

    kw_m = re.search(r'<meta\s+name="keywords"\s+content="(.*?)"', content, re.S)
    keywords = kw_m.group(1).strip() if kw_m else DEFAULT_KEYWORDS[category]

    return {
        "path": os.path.basename(path),
        "title": clean_text(title_m.group(1)),
        "date": dt,
        "has_time": has_time,
        "category": category,
        "res_count": len(res_blocks),
        "previews": previews,
        "keywords": keywords,
    }


def date_label(a, with_time=True):
    if with_time and a["has_time"]:
        return a["date"].strftime("%Y/%m/%d %H:%M")
    return a["date"].strftime("%Y/%m/%d")


def render_cards(articles):
    out = []
    for a in articles[:CARD_COUNT]:
        cat = a["category"]
        previews = "\n".join(
            f'    <div class="res-preview"><span class="res-no">{esc(no)}</span>{esc(text)}</div>'
            for no, text in a["previews"]
        )
        comment = f'💬 {a["res_count"]}件のコメント' if a["res_count"] else ""
        out.append(f'''  <article class="card" data-keywords="{esc(a["keywords"])}">
    <div class="card-meta">
      <span class="tag {cat}">{CATEGORY_LABEL[cat]}</span>
      <span>{date_label(a)}</span>
    </div>
    <h2 class="card-title"><a href="{esc(a["path"])}" style="color:inherit;text-decoration:none;">{esc(a["title"])}</a></h2>
{previews}
    <div class="affiliate-box"></div>
    <div class="card-footer">
      <span>{comment}</span>
      <a class="read-more" href="{esc(a["path"])}">続きを読む →</a>
    </div>
  </article>''')
    return "\n\n".join(out)


def render_list(articles):
    out = []
    for i, a in enumerate(articles[:LIST_COUNT]):
        cat = a["category"]
        color = THUMB_COLORS[i % len(THUMB_COLORS)]
        count = f'<span>💬 {a["res_count"]}</span>' if a["res_count"] else ""
        out.append(f'''    <a class="thumb-item" href="{esc(a["path"])}">
      <div class="thumb-box {color}">{THUMB_ICON[cat]}</div>
      <div class="thumb-body">
        <div class="thumb-title">{esc(a["title"])}</div>
        <div class="thumb-meta"><span class="tag {cat}">{CATEGORY_LABEL[cat]}</span><span>{date_label(a, False)}</span>{count}</div>
      </div>
    </a>''')
    return "\n".join(out)


def render_side(articles):
    out = []
    for a in articles[:SIDE_COUNT]:
        out.append(f'''    <div class="ranking-item">
      <div class="rank-body">
        <a class="rank-title" href="{esc(a["path"])}">{esc(a["title"])}</a>
        <span class="rank-cat">{CATEGORY_LABEL[a["category"]]} {date_label(a, False)}</span>
      </div>
    </div>''')
    return "\n".join(out)


def replace_block(page, name, body, indent):
    pattern = re.compile(
        rf"(<!-- AUTO:{name}:START -->)(.*?)(\s*<!-- AUTO:{name}:END -->)", re.S
    )
    if not pattern.search(page):
        raise SystemExit(f"[ERROR] index.html に AUTO:{name} の目印が見つかりません")
    return pattern.sub(lambda m: f"{m.group(1)}\n{body}\n{indent}<!-- AUTO:{name}:END -->", page, count=1)


def main():
    paths = sorted(glob.glob("article*.html"), key=article_number)
    articles = [a for a in (parse_article(p) for p in paths) if a]
    if not articles:
        print("[ERROR] 記事が1件も読み取れなかったため、index.html は変更しません")
        return

    # 新しい順。同じ日時ならファイル番号が大きい方を先に
    articles.sort(key=lambda a: (a["date"], article_number(a["path"])), reverse=True)

    with open(INDEX_PATH, encoding="utf-8") as f:
        page = f.read()

    new_page = page
    new_page = replace_block(new_page, "CARDS", render_cards(articles), "  ")
    new_page = replace_block(new_page, "LIST", render_list(articles), "    ")
    new_page = replace_block(new_page, "SIDE", render_side(articles), "    ")

    if new_page == page:
        print(f"[OK] 変更なし({len(articles)}件)")
        return

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(new_page)
    print(f"[OK] {len(articles)}件の記事で index.html を更新しました")


if __name__ == "__main__":
    main()
