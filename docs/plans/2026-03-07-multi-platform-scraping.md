# Multi-Platform Scraping Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand daily digest from "Qiita+Zenn combined best-of-1" to "1 best article per platform" across Qiita, Zenn, note, Reddit — posting 4 Discord threads per day.

**Architecture:** Add `note_scraper.py` and `reddit_scraper.py` following existing scraper patterns; update `summarizer.select_best()` with a `prefer_tech` flag for note; update `send_to_discord.post_best_article()` to accept platform name/emoji; refactor `main.py` to iterate a `PLATFORMS` list.

**Tech Stack:** Python 3.11, requests, BeautifulSoup4, google-generativeai (Gemini), Reddit public JSON API

---

## Context

- All scrapers return `list[dict]` with keys: `title`, `url`, `published_date`
- `Summarizer.select_best(articles)` returns the index of the best article
- `DiscordMessenger.post_best_article(article, summary)` creates a forum thread
- Tests live in `test_scrapers.py` (manual integration style — we add unit tests alongside)
- Run tests: `python -m pytest test_scrapers.py -v` (integration) or `python -m pytest -v` (all)

---

## Task 1: note_scraper.py

**Files:**
- Create: `note_scraper.py`
- Modify: `test_scrapers.py` (add unit test)

### Step 1: Write a failing unit test

Add this function to `test_scrapers.py`:

```python
from unittest.mock import patch, MagicMock

def test_note_scraper_returns_list():
    """NoteScraper.run() はリストを返す（実HTTPなし）"""
    from note_scraper import NoteScraper

    # note.com/trending のHTMLを最低限模倣したモック
    mock_html = """
    <html><body>
      <div class="o-favorite-count">
        <a href="https://note.com/user1/n/abc123">テスト記事1</a>
      </div>
      <div class="o-favorite-count">
        <a href="https://note.com/user2/n/def456">テスト記事2</a>
      </div>
    </body></html>
    """
    mock_resp = MagicMock()
    mock_resp.content = mock_html.encode("utf-8")
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.Session.get", return_value=mock_resp):
        scraper = NoteScraper(top_n=5)
        articles = scraper.run()

    assert isinstance(articles, list)
```

Run: `python -m pytest test_scrapers.py::test_note_scraper_returns_list -v`
Expected: **FAIL** — `ModuleNotFoundError: No module named 'note_scraper'`

### Step 2: Implement note_scraper.py

Create `note_scraper.py`:

```python
import datetime
import logging

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class NoteScraper:
    """note.comのトレンドから記事候補を取得するスクレイパー"""

    TRENDING_URL = "https://note.com/trending"
    JST = datetime.timezone(datetime.timedelta(hours=9))

    def __init__(self, top_n=15):
        self.top_n = top_n
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        today_jst = datetime.datetime.now(self.JST).date()
        self.yesterday_str = (today_jst - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        logging.info(f"note 対象日: {self.yesterday_str}")

    def run(self) -> list[dict]:
        """トレンドページから記事候補を取得する"""
        logging.info(f"note: トレンドページから記事取得中... {self.TRENDING_URL}")
        try:
            resp = self.session.get(self.TRENDING_URL, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            logging.error(f"note fetch error: {e}")
            return []

        soup = BeautifulSoup(resp.content, "html.parser")
        articles = []
        seen_urls: set = set()

        # note のトレンドページ: 記事リンクは /n/ を含むパス
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            # note記事のURLパターン: /n/xxxxxxxx
            if "/n/" not in href:
                continue
            url = href if href.startswith("http") else f"https://note.com{href}"
            if url in seen_urls:
                continue
            seen_urls.add(url)

            title = a_tag.get_text(strip=True)
            if not title or len(title) < 5:
                # タイトルが短すぎるリンクはスキップ（ナビゲーション等）
                continue

            articles.append({
                "title": title,
                "url": url,
                "published_date": self.yesterday_str,  # トレンド=昨日相当として扱う
            })
            if len(articles) >= self.top_n:
                break

        logging.info(f"note: {len(articles)} 件の記事候補を取得")
        return articles
```

### Step 3: Run the test to verify it passes

Run: `python -m pytest test_scrapers.py::test_note_scraper_returns_list -v`
Expected: **PASS**

### Step 4: Commit

```bash
git add note_scraper.py test_scrapers.py
git commit -m "feat: add note_scraper.py with trending page scraping"
```

---

## Task 2: reddit_scraper.py

**Files:**
- Create: `reddit_scraper.py`
- Modify: `test_scrapers.py` (add unit test)

### Step 1: Write a failing unit test

Add to `test_scrapers.py`:

```python
def test_reddit_scraper_returns_list():
    """RedditScraper.run() はリストを返す（実HTTPなし）"""
    from reddit_scraper import RedditScraper
    import json

    mock_data = {
        "data": {
            "children": [
                {"data": {
                    "title": "Test Tech Article",
                    "url": "https://example.com/article",
                    "permalink": "/r/technology/comments/abc/test/",
                    "score": 1500,
                    "created_utc": 1741305600,  # 2026-03-07 UTC
                }},
            ]
        }
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = mock_data
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.Session.get", return_value=mock_resp):
        scraper = RedditScraper(subreddit="technology", top_n=10)
        articles = scraper.run()

    assert isinstance(articles, list)
    assert len(articles) == 1
    assert articles[0]["title"] == "Test Tech Article"
```

Run: `python -m pytest test_scrapers.py::test_reddit_scraper_returns_list -v`
Expected: **FAIL** — `ModuleNotFoundError: No module named 'reddit_scraper'`

### Step 2: Implement reddit_scraper.py

Create `reddit_scraper.py`:

```python
import datetime
import logging

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class RedditScraper:
    """Redditの指定サブレディットからトップ投稿を取得するスクレイパー"""

    BASE_URL = "https://www.reddit.com/r/{subreddit}/top.json"
    JST = datetime.timezone(datetime.timedelta(hours=9))

    def __init__(self, subreddit="technology", top_n=10):
        self.subreddit = subreddit
        self.top_n = top_n
        self.session = requests.Session()
        # Redditは一般的なUser-Agentを拒否するため専用文字列を設定
        self.session.headers.update({
            "User-Agent": "TechDigest/1.0 (automated digest bot)"
        })
        today_jst = datetime.datetime.now(self.JST).date()
        self.yesterday_str = (today_jst - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        logging.info(f"Reddit r/{subreddit} 対象日: {self.yesterday_str}")

    def run(self) -> list[dict]:
        """サブレディットの当日トップ投稿を取得する"""
        url = self.BASE_URL.format(subreddit=self.subreddit)
        params = {"t": "day", "limit": self.top_n}
        logging.info(f"Reddit: {url} から取得中...")

        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logging.error(f"Reddit fetch error: {e}")
            return []

        articles = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            title = post.get("title", "")
            # 外部リンク投稿はpost["url"]、自己投稿はRedditのページを使う
            post_url = post.get("url", "")
            permalink = post.get("permalink", "")
            if not post_url and permalink:
                post_url = f"https://www.reddit.com{permalink}"
            # 自己投稿(reddit.com/r/...のURL)はRedditページ自体を指す
            if not post_url:
                continue

            articles.append({
                "title": title,
                "url": post_url,
                "score": post.get("score", 0),
                "published_date": self.yesterday_str,
            })

        # スコア順にソート
        articles.sort(key=lambda x: x["score"], reverse=True)
        logging.info(f"Reddit r/{self.subreddit}: {len(articles)} 件取得")
        return articles
```

### Step 3: Run the test to verify it passes

Run: `python -m pytest test_scrapers.py::test_reddit_scraper_returns_list -v`
Expected: **PASS**

### Step 4: Commit

```bash
git add reddit_scraper.py test_scrapers.py
git commit -m "feat: add reddit_scraper.py for r/technology top posts"
```

---

## Task 3: summarizer.py — prefer_tech フラグ追加

**Files:**
- Modify: `summarizer.py` (lines 15-40, `select_best` method)

### Step 1: Update `select_best` signature and prompt

`select_best` の引数に `prefer_tech: bool = False` を追加し、`True` のとき（noteなど全ジャンル対象のプラットフォーム用）はプロンプトに技術系優先の指示を追加する。

**変更箇所** `summarizer.py:15`:

```python
def select_best(self, articles: list[dict], prefer_tech: bool = False) -> int:
    """記事リストから最も価値のある1記事のインデックスを返す"""
    articles_text = "\n".join(
        f"{i+1}. {a['title']}" for i, a in enumerate(articles)
    )
    tech_hint = "\n- 技術・プログラミング・AI・開発関連の記事を最優先する" if prefer_tech else ""
    prompt = f"""
以下の記事リストから、最も技術的に価値があり、読者にとって有益な記事を1つ選んでください。
選定基準:
- 技術的な新規性・革新性
- 実用性の高さ
- 幅広いエンジニアに関連する内容
- トレンドへの関連性{tech_hint}

記事リスト:
{articles_text}

最も優れた記事の番号（数字のみ）を返してください。他の文字は一切含めないでください。
"""
    try:
        response = self.model.generate_content(prompt)
        index = int(response.text.strip()) - 1
        if 0 <= index < len(articles):
            return index
    except Exception as e:
        logger.error(f"記事選定エラー: {e}")
    return 0
```

### Step 2: Verify the change is backward-compatible

`prefer_tech=False` がデフォルトなので既存の呼び出し `summarizer.select_best(articles)` はそのまま動く。変更後に構文エラーがないことを確認:

Run: `python -c "from summarizer import Summarizer; print('OK')`
Expected: `OK`

### Step 3: Commit

```bash
git add summarizer.py
git commit -m "feat: add prefer_tech flag to Summarizer.select_best for note platform"
```

---

## Task 4: send_to_discord.py — プラットフォーム名対応

**Files:**
- Modify: `send_to_discord.py` (lines 13-58, `post_best_article` method)

### Step 1: Update `post_best_article` signature

`platform_name: str = "テック"` と `emoji: str = "🌟"` を追加し、スレッド名とヘッダーに使う。

**変更後の `post_best_article`**:

```python
def post_best_article(
    self,
    article: dict,
    summary: str,
    platform_name: str = "テック",
    emoji: str = "🌟",
) -> None:
    """本日の注目記事をDiscordフォーラムスレッドに投稿する"""
    today = datetime.date.today().strftime("%Y-%m-%d")
    thread_name = f"{today} {platform_name} 注目記事"

    header = (
        f"{emoji} **{platform_name} 注目記事** — {today}\n\n"
        f"**{article['title']}**\n"
        f"{article['url']}"
    )
    if len(header) > 2000:
        header = header[:1997] + "..."

    try:
        resp = requests.post(
            f"{self.webhook_url}?wait=true",
            json={"content": header, "thread_name": thread_name},
            timeout=10,
        )
        resp.raise_for_status()
        thread_id = resp.json().get("channel_id")
        if not thread_id:
            logger.error(
                "thread_id が取得できませんでした。レスポンス: %s", resp.json()
            )
            return
        logger.info(f"フォーラムスレッド作成: {thread_name} (id={thread_id})")
    except Exception as e:
        logger.error(f"フォーラムスレッド作成エラー: {e}")
        return

    detail = f"**解説:**\n{summary}"
    if len(detail) > 2000:
        detail = detail[:1997] + "..."
    try:
        requests.post(
            f"{self.webhook_url}?thread_id={thread_id}",
            json={"content": detail},
            timeout=10,
        ).raise_for_status()
        logger.info(f"解説投稿完了: {article['title']}")
    except Exception as e:
        logger.error(f"解説投稿エラー: {e}")
```

### Step 2: Verify backward-compatibility

既存の呼び出し `messenger.post_best_article(article, summary)` はデフォルト引数で動く。

Run: `python -c "from send_to_discord import DiscordMessenger; print('OK')"`
Expected: `OK`

### Step 3: Commit

```bash
git add send_to_discord.py
git commit -m "feat: add platform_name and emoji params to DiscordMessenger.post_best_article"
```

---

## Task 5: main.py — PLATFORMSリスト方式にリファクタリング

**Files:**
- Modify: `main.py`
- Modify: `main.py` — `fetch_article_text` に note/Reddit の content selector を追加

### Step 1: note/Reddit 対応を fetch_article_text に追加

`fetch_article_text` の content selector ブロック（`main.py:28-32`）に note と Reddit を追加:

```python
if "qiita.com" in url:
    content_elem = soup.find("section", class_="it-MdContent")
elif "zenn.dev" in url:
    content_elem = soup.find("div", class_="znc")
elif "note.com" in url:
    content_elem = soup.find("div", class_="note-common-styles__textnote-body")
elif "reddit.com" in url:
    content_elem = soup.find("div", attrs={"data-testid": "post-rtjson-content"})
```

### Step 2: main.py を PLATFORMS リスト方式に書き換える

`main()` 関数全体を以下に置き換える:

```python
def main():
    load_dotenv()

    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    google_api_key = os.getenv("GOOGLE_API_KEY")

    if not webhook_url or not google_api_key:
        logging.error("DISCORD_WEBHOOK_URL または GOOGLE_API_KEY が設定されていません")
        sys.exit(1)

    from note_scraper import NoteScraper
    from reddit_scraper import RedditScraper

    PLATFORMS = [
        ("Qiita",  "🗾", QiitaScraper(top_n=5),  False),
        ("Zenn",   "📚", ZennScraper(top_n=5),   False),
        ("note",   "📝", NoteScraper(top_n=15),  True),
        ("Reddit", "👽", RedditScraper(top_n=10), False),
    ]

    summarizer = Summarizer(google_api_key)
    messenger = DiscordMessenger(webhook_url=webhook_url)

    logging.info("=== 記事取得開始 ===")

    for platform_name, emoji, scraper, prefer_tech in PLATFORMS:
        logging.info(f"--- {platform_name} 処理開始 ---")
        articles = scraper.run()

        if not articles:
            logging.warning(f"{platform_name}: 記事が取得できませんでした。スキップします。")
            continue

        best_index = summarizer.select_best(articles, prefer_tech=prefer_tech)
        best_article = articles[best_index]
        logging.info(f"{platform_name} 選定: {best_article['title']}")

        text = fetch_article_text(best_article["url"])
        try:
            summary = summarizer.summarize(best_article["title"], text or best_article["title"])
        except Exception as e:
            logging.warning(f"要約取得失敗 ({best_article['title']}): {e}")
            summary = "（要約取得失敗）"

        messenger.post_best_article(best_article, summary, platform_name, emoji)

    logging.info("=== 完了 ===")
```

また、`main.py` の import 行に新スクレイパーを追加する（`from note_scraper import NoteScraper` など）。main 内に遅延importとして書いても可。

### Step 3: 動作確認（モックで全体フロー）

```bash
python -c "
import main
print('main.py import OK')
"
```
Expected: `main.py import OK`

### Step 4: test_scrapers.py に note/Reddit の統合テスト追加 (オプション)

既存の `test_scraping()` 関数を参考に、`test_note_scraping()` と `test_reddit_scraping()` を追加する。実行時は `python test_scrapers.py` で手動確認。

```python
def test_note_scraping():
    from note_scraper import NoteScraper
    print("=== Testing note Scraper ===")
    scraper = NoteScraper(top_n=5)
    articles = scraper.run()
    if articles:
        print(f"Success: Found {len(articles)} note articles.")
        print(f"First: {articles[0]['title']} ({articles[0]['url']})")
    else:
        print("Failed: No note articles found.")

def test_reddit_scraping():
    from reddit_scraper import RedditScraper
    print("=== Testing Reddit Scraper ===")
    scraper = RedditScraper(subreddit="technology", top_n=5)
    articles = scraper.run()
    if articles:
        print(f"Success: Found {len(articles)} Reddit articles.")
        print(f"First: {articles[0]['title']} ({articles[0]['url']})")
    else:
        print("Failed: No Reddit articles found.")
```

### Step 5: Commit

```bash
git add main.py test_scrapers.py
git commit -m "feat: refactor main.py to PLATFORMS list, add note/Reddit support"
```

---

## Task 6: 最終確認

### Step 1: 全ユニットテスト実行

```bash
python -m pytest test_scrapers.py -v -k "not test_scraping"
```
Expected: `test_note_scraper_returns_list PASSED`, `test_reddit_scraper_returns_list PASSED`

### Step 2: import チェック

```bash
python -c "
from note_scraper import NoteScraper
from reddit_scraper import RedditScraper
from summarizer import Summarizer
from send_to_discord import DiscordMessenger
import main
print('All imports OK')
"
```
Expected: `All imports OK`

### Step 3: 最終コミット（変更があれば）

```bash
git add -p
git commit -m "feat: multi-platform scraping (Qiita/Zenn/note/Reddit) 1 article each"
```
