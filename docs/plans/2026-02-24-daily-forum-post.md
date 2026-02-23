# Daily Forum Post Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 記事ごとに個別スレッドを作成する現在の動作を、1日1フォーラムスレッドにまとめて10記事一覧 + 各要約をスレッド内に投稿する動作に変更する。

**Architecture:** `send_to_discord.py` の `DiscordMessenger` クラスに `create_daily_forum_post()` メソッドを追加し、`main.py` で全記事・要約を収集してから一括で呼ぶ。旧メソッド `send_article_with_summary()` は削除する。

**Tech Stack:** Python, `requests` ライブラリ, Discord Webhook API (Forum channel)

---

### Task 1: `DiscordMessenger` を新 API に置き換える

**Files:**
- Modify: `send_to_discord.py`

**Step 1: `send_to_discord.py` 全体を以下の内容に書き換える**

```python
import datetime
import logging
import time

import requests

logger = logging.getLogger(__name__)


class DiscordMessenger:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def create_daily_forum_post(
        self, articles: list[dict], summaries: list[str]
    ) -> None:
        """1日分の記事一覧と各要約を1つのフォーラムスレッドに投稿する"""
        today = datetime.date.today().strftime("%Y-%m-%d")
        thread_name = f"{today} テックニュース"

        # 記事一覧メッセージを組み立てる
        lines = [f"📰 本日のテックニュース ({len(articles)}件)"]
        for i, article in enumerate(articles, 1):
            lines.append(f"{i}. [{article['title']}](<{article['url']}>)")
        index_content = "\n".join(lines)[:2000]

        # フォーラムへ投稿してスレッドを作成
        try:
            resp = requests.post(
                f"{self.webhook_url}?wait=true",
                json={"content": index_content, "thread_name": thread_name},
                timeout=10,
            )
            resp.raise_for_status()
            thread_id = resp.json().get("channel_id")
            logger.info(f"フォーラムスレッド作成: {thread_name} (id={thread_id})")
        except Exception as e:
            logger.error(f"フォーラムスレッド作成エラー: {e}")
            return

        # 各記事の要約をスレッドに投稿
        for article, summary in zip(articles, summaries):
            content = (
                f"📌 **{article['title']}**\n"
                f"{article['url']}\n\n"
                f"**要約:**\n{summary}"
            )
            if len(content) > 2000:
                content = content[:1997] + "..."
            try:
                requests.post(
                    f"{self.webhook_url}?thread_id={thread_id}",
                    json={"content": content},
                    timeout=10,
                ).raise_for_status()
                logger.info(f"要約投稿完了: {article['title']}")
            except Exception as e:
                logger.error(f"要約投稿エラー ({article['title']}): {e}")
            time.sleep(1)  # レート制限対策
```

**Step 2: 変更を確認する**

```bash
python -c "from send_to_discord import DiscordMessenger; print('OK')"
```

Expected: `OK`

**Step 3: コミット**

```bash
git add send_to_discord.py
git commit -m "refactor: DiscordMessenger を1日1スレッド方式に変更"
```

---

### Task 2: `main.py` を新 API に合わせて変更する

**Files:**
- Modify: `main.py`

**Step 1: `main()` 関数のループ部分を書き換える**

現在のコード (`main.py:69-79`) を以下に置き換える:

```python
    summaries = []
    for article in all_articles:
        logging.info(f"処理中: {article['title']}")
        text = fetch_article_text(article["url"])
        summary = summarizer.summarize(article["title"], text or article["title"])
        summaries.append(summary)
        time.sleep(2)

    messenger.create_daily_forum_post(all_articles, summaries)
```

**Step 2: 変更を確認する**

```bash
python -c "import main; print('OK')"
```

Expected: `OK`

**Step 3: コミット**

```bash
git add main.py
git commit -m "refactor: main.py を1日1スレッド方式に変更"
```

---

### Task 3: 動作確認

**Step 1: ドライラン（実際には送信しない簡易テスト）**

```bash
python -c "
from unittest.mock import patch, MagicMock
from send_to_discord import DiscordMessenger

articles = [
    {'title': 'テスト記事1', 'url': 'https://example.com/1'},
    {'title': 'テスト記事2', 'url': 'https://example.com/2'},
]
summaries = ['要約1の内容', '要約2の内容']

mock_resp = MagicMock()
mock_resp.json.return_value = {'channel_id': '123456789'}

with patch('requests.post', return_value=mock_resp) as mock_post:
    m = DiscordMessenger('https://discord.com/api/webhooks/test')
    m.create_daily_forum_post(articles, summaries)
    print(f'requests.post 呼び出し回数: {mock_post.call_count}')  # 3 (一覧1 + 要約2)
    # 最初の呼び出しで thread_name が含まれることを確認
    first_call_json = mock_post.call_args_list[0][1]['json']
    assert 'thread_name' in first_call_json, 'thread_name がない'
    assert 'テックニュース' in first_call_json['thread_name'], 'スレッド名が不正'
    print('テスト PASS')
"
```

Expected:
```
requests.post 呼び出し回数: 3
テスト PASS
```

**Step 2: 最終コミット（不要なら省略）**

```bash
git log --oneline -5
```

---
